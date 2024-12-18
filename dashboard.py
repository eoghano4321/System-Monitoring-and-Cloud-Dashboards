import logging
from dash import Dash, dependencies, dcc, html
from sqlalchemy.orm import Session
from models import MetricType, SystemMetricValue, SystemMetricSnapshot
from dash_daq import Gauge
from datetime import datetime

class Dashboard:
    def __init__(self):
        self.logger = logging.getLogger()

    def create_dash_app(self, webserver, engine):
        self.engine = engine
        session = Session(engine)

        # Fetch all metric types
        metric_types = session.query(MetricType).all()
        metric_type_options = [{'label': mt.metric_type, 'value': mt.metric_type} for mt in metric_types]
        session.close()

        dash_app = Dash(__name__, server=webserver, url_base_pathname='/dash/')
        dash_app.layout = html.Div([
            html.H1('System Metrics Dashboard'),
            # A 2x2 grid layout for the 4 divs, each with a dropdown for metric type and view type
            html.Div([
                html.Div([
                    dcc.Dropdown(
                        id='metric-type-dropdown-1',
                        options=metric_type_options,
                        placeholder='Select metric type 1',
                        multi=True
                    ),
                    dcc.RadioItems(
                        id='view-type-radio-1',
                        options=[
                            {'label': 'Gauge', 'value': 'gauge'},
                            {'label': 'Graph', 'value': 'graph'},
                            {'label': 'Table', 'value': 'table'}
                        ],
                        value='graph',
                        labelStyle={'display': 'inline-block'}
                    ),
                    html.Div(id='view-container-1')
                ], style={'padding': '10px'}),
                
                html.Div([
                    dcc.Dropdown(
                        id='metric-type-dropdown-2',
                        options=metric_type_options,
                        placeholder='Select metric type 2',
                        multi=True
                    ),
                    dcc.RadioItems(
                        id='view-type-radio-2',
                        options=[
                            {'label': 'Gauge', 'value': 'gauge'},
                            {'label': 'Graph', 'value': 'graph'},
                            {'label': 'Table', 'value': 'table'}
                        ],
                        value='graph',
                        labelStyle={'display': 'inline-block'}
                    ),
                    html.Div(id='view-container-2')
                ], style={'padding': '10px'}),
            ], style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '10px'}),  # 2x2 grid layout for divs
            
            html.Div([
                html.Div([
                    dcc.Dropdown(
                        id='metric-type-dropdown-3',
                        options=metric_type_options,
                        placeholder='Select metric type 3',
                        multi=True
                    ),
                    dcc.RadioItems(
                        id='view-type-radio-3',
                        options=[
                            {'label': 'Gauge', 'value': 'gauge'},
                            {'label': 'Graph', 'value': 'graph'},
                            {'label': 'Table', 'value': 'table'}
                        ],
                        value='graph',
                        labelStyle={'display': 'inline-block'}
                    ),
                    html.Div(id='view-container-3')
                ], style={'padding': '10px'}),
                
                html.Div([
                    dcc.Dropdown(
                        id='metric-type-dropdown-4',
                        options=metric_type_options,
                        placeholder='Select metric type 4',
                        multi=True
                    ),
                    dcc.RadioItems(
                        id='view-type-radio-4',
                        options=[
                            {'label': 'Gauge', 'value': 'gauge'},
                            {'label': 'Graph', 'value': 'graph'},
                            {'label': 'Table', 'value': 'table'}
                        ],
                        value='graph',
                        labelStyle={'display': 'inline-block'}
                    ),
                    html.Div(id='view-container-4')
                ], style={'padding': '10px'}),
            ], style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '10px'}),  # 2x2 grid layout for divs
            dcc.Interval(
                id='interval-component',
                interval=10000,  # Update every 10 seconds
                n_intervals=0
            )
        ])

        @dash_app.callback(
            [
                dependencies.Output('view-container-1', 'children'),
                dependencies.Output('view-container-2', 'children'),
                dependencies.Output('view-container-3', 'children'),
                dependencies.Output('view-container-4', 'children')
            ],
            [
                dependencies.Input('metric-type-dropdown-1', 'value'),
                dependencies.Input('metric-type-dropdown-2', 'value'),
                dependencies.Input('metric-type-dropdown-3', 'value'),
                dependencies.Input('metric-type-dropdown-4', 'value'),
                dependencies.Input('view-type-radio-1', 'value'),
                dependencies.Input('view-type-radio-2', 'value'),
                dependencies.Input('view-type-radio-3', 'value'),
                dependencies.Input('view-type-radio-4', 'value'),
                dependencies.Input('interval-component', 'n_intervals')
            ]
        )
        def update_views(metric_types_1, metric_types_2, metric_types_3, metric_types_4, view_type_1, view_type_2, view_type_3, view_type_4, n_intervals):
            # Create a list for each div's view output
            views = []

            # Process each dropdown and its corresponding view type
            for i, (metric_types, view_type) in enumerate([
                (metric_types_1, view_type_1),
                (metric_types_2, view_type_2),
                (metric_types_3, view_type_3),
                (metric_types_4, view_type_4)
            ]):
                if not metric_types or not view_type:
                    views.append(html.Div(f"Please select a metric type and a view type for div {i + 1}."))
                    continue

                session = Session(self.engine)
                try:
                    for metric_type in metric_types[:1]:  # Limit to 1 metric per dropdown
                        # Fetch the metric type ID
                        metric_type_obj = session.query(MetricType).filter_by(metric_type=metric_type).first()
                        if not metric_type_obj:
                            continue

                        # Fetch recent metric values along with timestamps
                        query = (
                            session.query(SystemMetricValue.metric_value, SystemMetricSnapshot.server_utc_timestamp_epoch)
                            .join(SystemMetricSnapshot, SystemMetricValue.metric_snapshot_id == SystemMetricSnapshot.metric_snapshot_id)
                            .filter(SystemMetricValue.metric_type_id == metric_type_obj.metric_type_id)
                            .order_by(SystemMetricSnapshot.server_utc_timestamp_epoch.desc())
                            .limit(10)
                        )
                        results = query.all()
                        results.reverse()

                        values = [float(r.metric_value) for r in results]
                        timestamps = [
                            datetime.utcfromtimestamp(r.server_utc_timestamp_epoch).strftime('%d-%m-%Y %H:%M:%S') 
                            for r in results
                        ]

                        # Generate the appropriate view based on the selected view type
                        if view_type == 'gauge':
                            if not values:
                                views.append(html.Div(f"No data for {metric_type}", style={'textAlign': 'center'}))
                                continue

                            current_value = values[-1]
                            min_value = min(min(values), 0)
                            max_value = max(max(values), 100)

                            views.append(
                                Gauge(
                                    id=f'{metric_type}-gauge',
                                    label={'label': metric_type, 'style': {'fontSize': '18px'}},
                                    min=min_value,
                                    max=max_value,
                                    value=current_value,
                                    showCurrentValue=True,
                                    color={"gradient": True, "ranges": {"green": [min_value, max_value * 0.7], "red": [max_value * 0.7, max_value]}}
                                )
                            )
                        elif view_type == 'graph':
                            views.append(
                                dcc.Graph(
                                    id=f'{metric_type}-graph',
                                    figure={
                                        'data': [
                                            {'x': timestamps, 'y': values, 'type': 'line', 'name': metric_type}
                                        ],
                                        'layout': {'title': metric_type}
                                    }
                                )
                            )
                        elif view_type == 'table':
                            views.append(
                                html.Table(
                                    children=[
                                        html.Tr([html.Th('Timestamp'), html.Th('Value')])
                                    ] + [
                                        html.Tr([html.Td(ts), html.Td(val)]) for ts, val in zip(timestamps, values)
                                    ]
                                )
                            )
                except Exception as e:
                    self.logger.error("Error updating views: %s", e)
                    views.append(html.Div(f"Error: {e}"))
                finally:
                    session.close()

            return views

        return dash_app
