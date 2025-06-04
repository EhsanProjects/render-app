# --- flask_app.py ---
from flask import Flask, request, render_template_string
from macys_login import get_commission
from datetime import datetime
from collections import defaultdict
import json

# import sys
# print("sys.prefix:", sys.prefix)
# print("sys.base_prefix:", sys.base_prefix)

app = Flask(__name__)
def format_dates_to_iso(data):
    for item in data:
        try:
            item["date"] = datetime.strptime(item["date"], "%m/%d/%Y").isoformat()
        except Exception:
            item["date"] = ""
    return data
def is_valid_amount(value):
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False

def prepare_weekly_comparison(p1_data, p2_data):
    def get_week_map(commissions):
        week_map = defaultdict(lambda: {
            "amount": 0.0, "hours": 0.0, "date": ""
        })
        for entry in commissions:
            try:
                date_obj = datetime.strptime(entry["date"], "%m/%d/%Y")
            except (ValueError, TypeError):
                continue
            week_number = str(date_obj.isocalendar().week)
            amount = float(entry.get("amount", 0.0)) if is_valid_amount(entry.get("amount")) else 0.0
            hours = float(entry.get("productive_hours", 0.0)) if is_valid_amount(entry.get("productive_hours")) else 0.0

            # Save latest date (or any date for the week)
            if not week_map[week_number]["date"]:
                week_map[week_number]["date"] = entry["date"]

            week_map[week_number]["amount"] += amount
            week_map[week_number]["hours"] += hours
        return week_map

    week_map_1 = get_week_map(p1_data)
    week_map_2 = get_week_map(p2_data)
    # all_weeks = sorted(set(week_map_1.keys()) | set(week_map_2.keys()), key=lambda w: int(w))
    # Combine all unique week keys from both maps
    all_weeks = list(set(week_map_1.keys()) | set(week_map_2.keys()))

    # Sort by the actual date (parsed from either map)
    def get_sort_date(week_key):
        date_str = week_map_1.get(week_key, {}).get("date") or week_map_2.get(week_key, {}).get("date")
        return datetime.strptime(date_str, "%m/%d/%Y") if date_str else datetime.min

    all_weeks.sort(key=get_sort_date)


    comparison_data = []
    for week in all_weeks:
        w1 = week_map_1.get(week, {"amount": 0.0, "hours": 0.0, "date": ""})
        w2 = week_map_2.get(week, {"amount": 0.0, "hours": 0.0, "date": ""})
        diff = w2["amount"] - w1["amount"]
        pct_change = (diff / w1["amount"] * 100) if w1["amount"] else ("∞" if w2["amount"] else 0.0)
        comparison_data.append({
            "week": week,
            "date1": w1["date"],
            "period1_amount": w1["amount"],
            "period1_hours": w1["hours"],
            "date2": w2["date"],
            "period2_amount": w2["amount"],
            "period2_hours": w2["hours"],
            "diff": diff,
            "pct_change": pct_change
        })
    return comparison_data

@app.route("/", methods=["GET", "POST"])
def compare_commissions():
    commissions1, commissions2 = [], []
    total1 = total2 = total_hours1 = total_hours2 = 0
    period1_start = period1_end = period2_start = period2_end = ""
    comparison_data = []

    if request.method == "POST":
        employee_id = request.form["employee_id"]
        password = request.form["password"]
        period1_start = request.form["period1_start"]
        period1_end = request.form["period1_end"]
        period2_start = request.form["period2_start"]
        period2_end = request.form["period2_end"]

        try:
            datetime.strptime(period1_start, "%m/%d/%Y")
            datetime.strptime(period1_end, "%m/%d/%Y")
            datetime.strptime(period2_start, "%m/%d/%Y")
            datetime.strptime(period2_end, "%m/%d/%Y")
        except ValueError:
            return "<p>Invalid date format. Please use MM/DD/YYYY.</p>"

        try:
            commissions1 = get_commission(employee_id, password, period1_start, period1_end)
        except Exception as e:
            print("Error fetching period 1:", e)
        try:
            commissions2 = get_commission(employee_id, password, period2_start, period2_end)
        except Exception as e:
            print("Error fetching period 2:", e)

        total1 = sum(float(c["amount"]) for c in commissions1 if is_valid_amount(c.get("amount")))
        total2 = sum(float(c["amount"]) for c in commissions2 if is_valid_amount(c.get("amount")))
        total_hours1 = sum(float(c["productive_hours"]) for c in commissions1 if is_valid_amount(c.get("productive_hours")))
        total_hours2 = sum(float(c["productive_hours"]) for c in commissions2 if is_valid_amount(c.get("productive_hours")))

        comparison_data = prepare_weekly_comparison(commissions1, commissions2)

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Macy's Commission Comparison</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
    <style>
        body { font-family: Arial, sans-serif; padding: 30px; }
        input[type=text], input[type=password], input[type=submit] {
            width: 280px; padding: 8px; margin: 5px 0;
        }
        input[type=submit] {
            background-color: #4CAF50; color: white; border: none; cursor: pointer;
        }
        .table-container { display: flex; gap: 40px; margin-top: 20px; flex-wrap: wrap; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 30px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: center; }
        th { background-color: #f2f2f2; }
        canvas { margin-top: 30px; width: 100% !important; max-width: 1000px; }
    </style>
</head>
<body>

<h2>Compare Macy's Commission Between Two Periods</h2>
<form method="post">
    <label>Employee ID:</label><br><input type="text" name="employee_id" required><br>
    <label>Password:</label><br><input type="password" name="password" required><br><br>
    <label>Period 1 Start:</label><br><input type="text" name="period1_start" required><br>
    <label>Period 1 End:</label><br><input type="text" name="period1_end" required><br><br>
    <label>Period 2 Start:</label><br><input type="text" name="period2_start" required><br>
    <label>Period 2 End:</label><br><input type="text" name="period2_end" required><br><br>
    <input type="submit" value="Compare Commissions,Hours,Productivity">
</form>

{% if commissions1 or commissions2 %}

                            
    <!-- Weekly Line Chart -->
    <div style="width: 100%; margin-top: 30px;">
        <h3>Weekly Commission Line Chart</h3>
        <div style="display: flex; gap: 20px; flex-wrap: wrap;">
            <div style="flex: 1 1 100%;">
                <canvas id="comparisonChart" style="width: 100%; max-width: 100%; height: 400px;"></canvas>
            </div>
        </div>
    </div>


<div style="margin-top: 30px;">
    <h3>Weekly Breakdown Bar Chart</h3>
    <div>
        <button onclick="updateBarChart('commission')">Commission</button>
        <button onclick="updateBarChart('hours')">Hours</button>
        <button onclick="updateBarChart('productivity')">Productivity</button>
    </div>
    <canvas id="weeklyBarChart" style="width: 100%; max-width: 100%; height: 400px;"></canvas>
</div>



    <!-- Weekly Comparison Table -->
    <h3>Weekly Comparison Breakdown</h3>
    <div class="comparison-table-wrapper" style="display: flex; gap: 20px; flex-wrap: wrap;">

        <!-- Period 1 Table -->
        <div style="flex: 1;">
            <h4>Period 1: {{ period1_start }} to {{ period1_end }}</h4>
            <table>
                <tr>
                    <th>Week #</th>
                    <th>Date</th>
                    <th>Commission</th>
                    <th>Hours</th>
                </tr>
                {% for row in comparison_data %}
                <tr>
                    <td>{{ row.week }}</td>
                    <td>{{ row.date1 }}</td>
                    <td>${{ "%.2f"|format(row.period1_amount) }}</td>
                    <td>{{ "%.2f"|format(row.period1_hours) }}</td>
                </tr>
                {% endfor %}
                <tr style="font-weight: bold; background-color: #f9f9f9;">
                    <td>Total</td>
                    <td></td>
                    <td>${{ '%.2f'|format(total1) }}</td>
                    <td>{{ '%.2f'|format(total_hours1) }}</td>
                </tr>
            </table>
        </div>

        <!-- Period 2 Table -->
        <div style="flex: 1;">
            <h4>Period 2: {{ period2_start }} to {{ period2_end }}</h4>
            <table>
                <tr>
                    <th>Week #</th>
                    <th>Date</th>
                    <th>Commission</th>
                    <th>Hours</th>
                </tr>
                {% for row in comparison_data %}
                <tr>
                    <td>{{ row.week }}</td>
                    <td>{{ row.date2 }}</td>
                    <td>${{ "%.2f"|format(row.period2_amount) }}</td>
                    <td>{{ "%.2f"|format(row.period2_hours) }}</td>
                </tr>
                {% endfor %}
                <tr style="font-weight: bold; background-color: #f9f9f9;">
                    <td>Total</td>
                    <td></td>
                    <td>${{ '%.2f'|format(total2) }}</td>
                    <td>{{ '%.2f'|format(total_hours2) }}</td>
                </tr>
            </table>
        </div>

        <!-- Summary Table -->
        <div style="flex: 1;">
            <h4>Summary</h4>
            <table>
                <tr>
                    <th>Week #</th>
                    <th>Δ Commission → %</th>
                    <th>Δ Hours → %</th>
                    <th>Δ Productivity → %</th>
                </tr>
                {% for row in comparison_data %}
                <tr>
                    <td>{{ row.week }}</td>
                    <td style="color: {{ 'red' if row.diff < 0 or (row.pct_change != '∞' and row.pct_change < 0) else 'black' }};">
                        ${{ "%.2f"|format(row.diff) }} → 
                        {{ row.pct_change if row.pct_change == '∞' else "%.1f"|format(row.pct_change) }}%
                    </td>
                    {% set hour_diff = row.period2_hours - row.period1_hours %}
                    {% set hour_pct = (hour_diff / row.period1_hours * 100) if row.period1_hours else ('∞' if row.period2_hours else 0.0) %}
                    <td style="color: {{ 'red' if hour_diff < 0 else 'black' }};">
                        {{ "%.2f"|format(hour_diff) }} → 
                        {{ hour_pct if hour_pct == '∞' else "%.1f"|format(hour_pct) }}%
                    </td>
                    {% set prod1 = (row.period1_amount / row.period1_hours) if row.period1_hours else 0 %}
                    {% set prod2 = (row.period2_amount / row.period2_hours) if row.period2_hours else 0 %}
                    {% set prod_diff = prod2 - prod1 %}
                    {% set prod_pct = (prod_diff / prod1 * 100) if prod1 else ("∞" if prod2 else 0) %}
                    <td style="color: {{ 'red' if prod_diff < 0 else 'green' }};">
                        {{ "%.2f"|format(prod_diff) }} → {{ prod_pct if prod_pct == '∞' else "%.1f"|format(prod_pct) }}%
                    </td>
                </tr>
                {% endfor %}
                <tr style="font-weight: bold; background-color: #f9f9f9;">
                    <td>Total</td>
                    <td style="color: {{ 'red' if (total2 - total1) < 0 else 'green' }};">
                        ${{ '%.2f'|format(total2 - total1) }} → {{ '%.2f'|format((total2 - total1)/total1*100) }}%
                    </td>
                    <td style="color: {{ 'red' if (total_hours2 - total_hours1) < 0 else 'green' }};">
                        {{ '%.2f'|format(total_hours2 - total_hours1) }} → {{ '%.2f'|format((total_hours2 - total_hours1)/total_hours1*100) }}%
                    </td>
                    <td style="color: {{ 'red' if (total2/total_hours2 - total1/total_hours1) < 0 else 'green' }};">
                        {{ '%.2f'|format(total2/total_hours2 - total1/total_hours1) }} →
                        {{ '%.2f'|format(((total2/total_hours2 - total1/total_hours1)/(total1/total_hours1))*100) }}%
                    </td>
                </tr>
            </table>
        </div>

    </div>

    <!-- Chart Scripts -->
    <script>
    const rawData1 = {{ commissions1 | tojson | safe }};
    const rawData2 = {{ commissions2 | tojson | safe }};
    const weeklyData = {{ comparison_data | tojson | safe }};

    // Processed datasets
    const dateData1 = rawData1.map(e => ({ x: new Date(e.date), y: parseFloat(e.amount) }));
    const dateData2 = rawData2.map(e => ({ x: new Date(e.date), y: parseFloat(e.amount) }));

    const weekData1 = weeklyData.map(e => ({ x: "W" + e.week, y: e.period1_amount }));
    const weekData2 = weeklyData.map(e => ({ x: "W" + e.week, y: e.period2_amount }));

    let comparisonChart = new Chart(document.getElementById('comparisonChart'), {
        type: 'line',
        data: {
            datasets: [
                { label: 'Period 1', data: dateData1, borderColor: 'blue', tension: 0.3 },
                { label: 'Period 2', data: dateData2, borderColor: 'red', tension: 0.3 }
            ]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    type: 'time',
                    time: { unit: 'week' },
                    title: { display: true, text: 'Date' }
                },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Commission ($)' }
                }
            }
        }
    });

    function updateLineChartXAxis() {
        const selected = document.getElementById("xAxisSelector").value;
        if (selected === "date") {
            comparisonChart.data.datasets[0].data = dateData1;
            comparisonChart.data.datasets[1].data = dateData2;
            comparisonChart.options.scales.x = {
                type: 'time',
                time: { unit: 'week' },
                title: { display: true, text: 'Date' }
            };
        } else {
            comparisonChart.data.datasets[0].data = weekData1;
            comparisonChart.data.datasets[1].data = weekData2;
            comparisonChart.options.scales.x = {
                type: 'category',
                title: { display: true, text: 'Week Number' }
            };
        }
        comparisonChart.update();
    }
    {% if comparison_data %}
    
        const comparisonData = {{ comparison_data | tojson | safe }};
        const weeks = comparisonData.map(r => "W" + r.week);

        const datasetMap = {
            commission: [
                { label: 'P1 Commission', data: comparisonData.map(r => r.period1_amount), backgroundColor: 'rgba(54, 162, 235, 0.6)' },
                { label: 'P2 Commission', data: comparisonData.map(r => r.period2_amount), backgroundColor: 'rgba(255, 99, 132, 0.6)' }
            ],
            hours: [
                { label: 'P1 Hours', data: comparisonData.map(r => r.period1_hours), backgroundColor: 'rgba(153, 102, 255, 0.6)' },
                { label: 'P2 Hours', data: comparisonData.map(r => r.period2_hours), backgroundColor: 'rgba(255, 159, 64, 0.6)' }
            ],
            productivity: [
                { label: 'P1 Productivity', data: comparisonData.map(r => r.period1_hours > 0 ? r.period1_amount / r.period1_hours : 0), backgroundColor: 'rgba(75, 192, 192, 0.6)' },
                { label: 'P2 Productivity', data: comparisonData.map(r => r.period2_hours > 0 ? r.period2_amount / r.period2_hours : 0), backgroundColor: 'rgba(255, 206, 86, 0.6)' }
            ]
        };

        let barChart = new Chart(document.getElementById('weeklyBarChart'), {
            type: 'bar',
            data: {
                labels: weeks,
                datasets: datasetMap['commission']
            },
            options: {
                responsive: true,
                scales: {
                    x: { stacked: false, title: { display: true, text: 'Week Number' }},
                    y: { beginAtZero: true, title: { display: true, text: 'Value' }}
                }
            }
        });

        function updateBarChart(type) {
            barChart.data.datasets = datasetMap[type];
            barChart.update();
        }
    
    {% endif %}
    
        
    </script>

{% endif %}

</body>
</html>
    """, commissions1=commissions1, commissions2=commissions2,
         period1_start=period1_start, period1_end=period1_end,
         period2_start=period2_start, period2_end=period2_end,
         total1=total1, total2=total2,
         total_hours1=total_hours1, total_hours2=total_hours2,
         comparison_data=comparison_data)

if __name__ == "__main__":
    app.run()
