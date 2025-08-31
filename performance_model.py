import flet as ft

# Function to create the performance model tab
def performance_model_tab():
    performance_data = {
        "LSTM": {"Accuracy": 0.92, "Precision": 0.93, "Recall": 0.91},
        "GRU": {"Accuracy": 0.90, "Precision": 0.92, "Recall": 0.88},
        "Random Forest (n=100)": {"Accuracy": 0.89, "Precision": 0.91, "Recall": 0.87},
        "ARIMA": {"Accuracy": 0.85, "Precision": 0.86, "Recall": 0.84},
        "SARIMA": {"Accuracy": 0.83, "Precision": 0.85, "Recall": 0.82},
    }

    results_table = ft.DataTable(columns=[
        ft.DataColumn(ft.Text("Model")),
        ft.DataColumn(ft.Text("Accuracy")),
        ft.DataColumn(ft.Text("Precision")),
        ft.DataColumn(ft.Text("Recall")),
    ])
    
    for model_name, metrics in performance_data.items():
        results_table.rows.append(ft.DataRow(cells=[
            ft.DataCell(ft.Text(model_name)),
            ft.DataCell(ft.Text(f"{metrics['Accuracy']:.2f}")),
            ft.DataCell(ft.Text(f"{metrics['Precision']:.2f}")),
            ft.DataCell(ft.Text(f"{metrics['Recall']:.2f}")),
        ]))

    return ft.Column([
        ft.Text("Model Performance Metrics", size=22, weight="bold"),
        results_table
    ], spacing=20)
