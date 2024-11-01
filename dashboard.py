import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from datetime import datetime
import os
import pickle
import threading
import time
import logging

from data_source import fetch_station_values, fetch_essn_values

app = dash.Dash(__name__, external_stylesheets=['/assets/styles.css'])

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),  # Log to file
        logging.StreamHandler()  # Also log to console
    ]
)

# File to store MUF data
MUF_DATA_FILE = "muf_data.pkl"
ESSN_DATA_FILE = "essn_data.pkl"

# Size limit for the data files (in bytes)
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB

FETCH_INTERVAL = 300  # Fetch data every 5 minutes (300 seconds)

# Load data if it exists
def load_data(file):
    if os.path.exists(file):
        with open(file, "rb") as f:
            return pickle.load(f)
    return []

# Save data to file
def save_data(file, var):
    # Check the file size before saving
    if os.path.exists(file) and os.path.getsize(file) >= MAX_FILE_SIZE:
        # Remove oldest entries until file size is under the limit
        while os.path.exists(file) and os.path.getsize(file) >= MAX_FILE_SIZE:
            var.pop(0)  # Remove the oldest data point
            with open(file, "wb") as f:
                pickle.dump(var, f)
    with open(file, "wb") as f:
        pickle.dump(var, f)

# Global variable to hold fetched data
muf_data = load_data(MUF_DATA_FILE)
essn_data = load_data(ESSN_DATA_FILE)


# Function to fetch and store MUF data
def fetch_muf_data():
    logger = logging.getLogger('fetch_muf_data')
    data = fetch_station_values()
    muf_data.append(data)
    save_data(MUF_DATA_FILE, muf_data)
    logger.info(f"Fetched MUF data")


# Function to fetch and store SSN data
def fetch_essn_data():
    logger = logging.getLogger('fetch_essn_data')
    data = fetch_essn_values()
    essn_data.append(data)
    save_data(ESSN_DATA_FILE, essn_data)
    logger.info(f"Fetched ESSN data")

# Background Data Fetching Thread
def background_data_fetch():
    while True:
        fetch_muf_data()
        fetch_essn_data()
        time.sleep(FETCH_INTERVAL)  # Wait for the defined interval

# Background Data Fetching Thread
def background_data_fetch():
    while True:
        fetch_muf_data()
        fetch_essn_data()
        time.sleep(FETCH_INTERVAL)  # Wait for the defined interval

# Start the background thread
data_thread = threading.Thread(target=background_data_fetch, daemon=True)
data_thread.start()

# Initial fetch if data is empty
if not muf_data:
    fetch_muf_data()

if not essn_data:
    fetch_essn_data()


# Helper function to create the highlighted text and graph section
def create_highlighted_section(text_id, graph_id, color, style):
    return html.Div(
        style={'display': 'flex', 'align-items': 'center', 'justify-content': 'center', 'marginTop': '20px'},
        children=[
            # Highlighted text section with class "highlight"
            html.Div(
                id=text_id,
                className=f'{style}',  # Apply the common "highlight" class
                children=[
                    html.H3(id=f'{text_id}-content',
                            style={
                                'font-weight': 'bold',
                                'color': f'{color}',
                                'font-size': '2em',
                                'margin': '0',
                                'textAlign': 'center'
                            })
                ]
            ),
            # Graph section
            dcc.Graph(id=graph_id, style={'flex': '1', 'margin': '0 20px'})
        ]
    )


# Update layout
app.layout = html.Div([
    dcc.Interval(id='interval-fetch', interval=60 * 5000, n_intervals=0),
    dcc.Interval(id='interval-update', interval=60 * 5000, n_intervals=0),
    html.H1("CQ7DX Real-Time HF Propagation Dashboard"),

    # Parent container holding both highlighted sections
    html.Div(
        id='highlight-sections-container',
        children=[
            # Original highlighted section
            create_highlighted_section('highlight', 'muf-graph', 'lightgreen', "highlight-green"),

            # Label Section for MUF and Critical Frequency
            html.Div(
                id='labels-container',
                style={'display': 'flex', 'justify-content': 'center', 'marginTop': '10px'},
                children=[
                    html.Div(
                        style={'display': 'flex', 'align-items': 'center', 'marginRight': '20px'},
                        children=[
                            html.Div(style={'width': '15px', 'height': '15px', 'backgroundColor': 'lightgreen',
                                            'marginRight': '5px'}),
                            html.Span("MUF (Maximum Usable Frequency)")
                        ]
                    ),
                    html.Div(
                        style={'display': 'flex', 'align-items': 'center'},
                        children=[
                            html.Div(
                                style={'width': '15px', 'height': '15px', 'backgroundColor': 'skyblue',
                                       'marginRight': '5px'}),
                            html.Span("foF2 (Critical Frequency)")
                        ]
                    ),
                ]
            ),

            # Duplicated highlighted section
            create_highlighted_section('highlight-duplicate', 'muf-graph-duplicate', 'red', 'highlight-red'),
        ]
    ),

    html.Div(id='footer', style={'textAlign': 'center', 'marginTop': '20px'}),
    # Meta refresh tag for auto-refreshing the browser
    html.Script('setInterval(function() { window.location.reload(); }, 5 * 60000);')  # Refresh every 5 minutes
])


@app.callback(
    Output('interval-fetch', 'n_intervals'),
    Input('interval-fetch', 'n_intervals')
)
def fetch_data_callback(n_intervals):
    fetch_muf_data()
    fetch_essn_data()
    return n_intervals


@app.callback(
    [Output('highlight-content', 'children'),
     Output('muf-graph', 'figure'),
     Output('highlight-duplicate-content', 'children'),  # Duplicated output for ESSN text
     Output('muf-graph-duplicate', 'figure'),  # Duplicated output for ESSN graph
     Output('footer', 'children')],
    Input('interval-update', 'n_intervals')
)
def update_muf_data(n_intervals):
    # Update MUF data
    latest_entry = muf_data[-1]
    latest_muf = latest_entry['muf']
    latest_fof2 = latest_entry['fof2']
    latest_time = latest_entry['time']

    # Convert times to datetime objects for MUF plotting
    times = [datetime.strptime(entry['time'], '%Y-%m-%dT%H:%M:%S') for entry in muf_data]
    muf_levels = [entry['muf'] for entry in muf_data]
    fof2_levels = [entry['fof2'] for entry in muf_data]

    # Create MUF figure
    fig_muf = go.Figure()
    fig_muf.add_trace(go.Scatter(
        x=times,
        y=muf_levels,
        mode='lines+markers',
        name='MUF',
        line=dict(color='lightgreen')
    ))

    fig_muf.add_trace(go.Scatter(
        x=times,
        y=fof2_levels,
        mode='lines+markers',
        name='Critical Frequency (foF2)',
        line=dict(color='skyblue')
    ))

    # Adding horizontal markers for MUF
    marker_levels = [3, 7, 14, 21, 28]
    for level in marker_levels:
        fig_muf.add_shape(
            type="line",
            x0=times[0], x1=times[-1],
            y0=level, y1=level,
            line=dict(color="red", width=1, dash="dash"),
            xref="x", yref="y"
        )
        fig_muf.add_annotation(
            x=times[-1],
            y=level,
            text=f"{level} MHz",
            showarrow=False,
            xanchor="left",
            font=dict(color="red"),
            align="left"
        )

    fig_muf.update_layout(
        title="MUF and foF2 Levels Over Time",
        xaxis_title="Time",
        yaxis_title="Frequency (MHz)",
        template="plotly_dark",
        showlegend=False,
        xaxis=dict(
            tickformat="%H:%M",
            dtick=60000 * 30
        )
    )

    # Update ESSN data
    latest_essn_entry = essn_data[-1]
    latest_ssn = latest_essn_entry['ssn']
    latest_sfi = latest_essn_entry['sfi']
    latest_essn_time = latest_essn_entry['time']

    # Convert times to datetime objects for ESSN plotting
    essn_times = [entry['time'] for entry in essn_data]
    essn_ssns = [entry['ssn'] for entry in essn_data]
    essn_sfis = [entry['sfi'] for entry in essn_data]

    # Create ESSN figure
    fig_essn = go.Figure()
    fig_essn.add_trace(go.Scatter(
        x=essn_times,
        y=essn_ssns,
        mode='lines+markers',
        name='SSN',
        line=dict(color='red')
    ))

    fig_essn.add_trace(go.Scatter(
        x=essn_times,
        y=essn_sfis,
        mode='lines+markers',
        name='SFI',
        line=dict(color='blue')
    ))

    fig_essn.update_layout(
        title="SSN and SFI Over Time",
        xaxis_title="Time",
        yaxis_title="Values",
        template="plotly_dark",
        showlegend=True,
        xaxis=dict(
            tickformat="%H:%M",
            dtick=60000 * 30
        )
    )

    highlighted_text = f"{latest_muf} MHz"
    highlighted_duplicate_text = f"**SSN **{latest_ssn}\n\n**SFI **{latest_sfi}"
    footer_text = f"Last updated: {latest_time}. Data location: El Arenosillo, Spain"

    # Return for original and duplicate components
    return highlighted_text, fig_muf, dcc.Markdown(highlighted_duplicate_text), fig_essn, footer_text


if __name__ == '__main__':
    app.run_server(debug=True)