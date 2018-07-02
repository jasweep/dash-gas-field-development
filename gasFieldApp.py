# -*- coding: utf-8 -*-
import math
#from numba import jit
import plotly as ply
import dash
import dash_auth
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go

from datetime import datetime as dt


# Setup of Classes

class Well(object):

    def __init__(self, flowRate, name='Well ?'):
        self.name = name
        self.age = 0
        self.timeFlowing = 0
        self.status = 'Standby'
        self.flowRate = flowRate

    def getName(self):
        return self.name

    def getAge(self):
        return self.age

    def setAge(self, age):
        self.age = age

    def getTimeFlowing(self):
        return self.timeFlowing

    def setTimeFlowing(self, time):
        self.timeFlowing = time

    def getStatus(self):
        return self.status

    def setStatus(self, status):
        self.status = status

    def getFlow(self):
        return self.flowRate

    def setFlow(self, flow):
        self.flowRate = flow


class Field(object):

    def __init__(self, name):
        self.name = name
        self.wells = []
        self.numWells = 0
        self.flowRate = 0

    def getFlow(self):
        flow = 0.0
        for well in wells:
            flow += well.getFlow()
        return flow


# Setup of Functions

# Decline curve
def decline(qi, d, t):
    return qi*math.exp(-d*t)

#@jit(nopython=True)
def simulateField(params):
    # economic parameters
    gasPriceRaw = params['gasPrice'] #3.0 # USD/GJ
    USDAUD = params['exchangeRate'] #1.31 # $
    gasPrice = gasPriceRaw*USDAUD # AUD/GJ
    costToDrill = params['costToDrill']*1.0E6 #3.0E6 # $
    costToFrac = params['costToFrac']*1.0E6 #2.0E6 # $
    costToTieIn = params['costToTieIn']*1.0E6 #0.5E6 # $

    # reservoir parameters
    aveMaxFlow = params['aveFlow']*1.0E6 # scf/day
    aveDeclineTime = params['aveDecline']*365.0 # days to 10%
    expParam = 2.30259/aveDeclineTime # param for exp decline curve

    # well construction parameters
    drillTime = params['drillTime'] # days
    drillToFracTime = params['fracWaitTime'] # days
    fracTime = params['fracTime'] # days
    fracToFlowTime = params['pipeWaitTime'] # days
    totalNonFlowTime = drillTime + drillToFracTime + fracTime + fracToFlowTime # days

    # field construction parameters
    rigsOperating = params['numRigs']

    # target flow rate
    flowTarget = params['tgtFlow'] # TJ/day
    flowTargetCF = flowTarget*947817.12 # cubicfeet/day

    # simulation parameters
    t_init = 0.0
    t_fin = params['simTime']*365.0


    # Algorithm
    field = Field('Fairfields')
    field.wells = [Well(aveMaxFlow) for i in range(rigsOperating)]

    tArr = []
    qArr = []
    decArr = []

    expenseArr = []
    incomeArr = []
    exposureArr = []
    numWellArr = []

    fieldExpense = 0
    fieldIncome = 0

    t = 0
    while t <= t_fin:
        fieldFlow = 0.0

        if t%drillTime == 0 and t > 1:
            field.wells = field.wells + [Well(aveMaxFlow) for i in range(rigsOperating)]

        for well in field.wells:

            # Add to Field Expense
            if well.age == drillTime:
                fieldExpense += costToDrill
            if well.age == drillTime + drillToFracTime + fracTime:
                fieldExpense += costToFrac
            if well.age == totalNonFlowTime:
                fieldExpense += costToTieIn

            timeFlowing = well.age - totalNonFlowTime

            if timeFlowing > 0:
                flowRate = decline(aveMaxFlow, expParam, timeFlowing)
                well.flowRate = flowRate

                if field.wells.index(well) == 0:
                    decArr.append(flowRate)

                fieldFlow += flowRate

                fieldIncome += gasPrice*flowRate/947.8171

            well.age += 1

        tArr.append(t)
        qArr.append(fieldFlow)
        expenseArr.append(fieldExpense)
        incomeArr.append(fieldIncome)
        exposureArr.append(fieldIncome - fieldExpense)
        numWellArr.append(len(field.wells))

        t += 1

    return tArr, qArr, expenseArr, incomeArr, decArr, exposureArr, numWellArr


# Setup of Web App
VALID_UNAME_PWORD_PAIRS =  [
    ['Jack', 'Tristar1'],
    ['Butler', 'Fairfields']
]


app = dash.Dash('auth')
auth = dash_auth.BasicAuth(
    app,
    VALID_UNAME_PWORD_PAIRS
)

#app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/bWLwgP.css"})
app.css.append_css({'external_url': 'https://cdn.rawgit.com/plotly/dash-app-stylesheets/2d266c578d2a6e8850ebce48fdb52759b2aef506/stylesheet-oil-and-gas.css'})
#app.css.append_css({"external_url": "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap-theme.min.css"})


# INITIAL RUN OF SIM
params = {
    'simTime': 5,
    'tgtFlow': 25.0,
    'numRigs': 2,
    'drillTime': 30,
    'fracWaitTime': 60,
    'fracTime': 10,
    'pipeWaitTime': 160,
    'aveFlow': 1.0,
    'aveDecline': 4,
    'gasPrice': 10.0,
    'exchangeRate': 1.31,
    'costToDrill': 3.0,
    'costToFrac': 2.0,
    'costToTieIn': 0.5,
    'numPhases': 1
}

tArr, qArr, expenseArr, incomeArr, decArr, exposureArr, numWellArr = simulateField(params)

app.layout = html.Div(className='container-fluid', children=[

    html.Div(className="row", children=[
        html.H1(children='Gas Field Development Tool'),

        html.Div('A web app analysis tool for natural gas field develop (based on no water)')
    ]),

    html.Div(id='graphs', className="row", children=[

        html.Div(className="four columns", children=[
            dcc.Graph(
                id='decline-vs-time',
                figure={
                    'data': [
                        go.Scatter(
                            x=tArr,
                            y=decArr,
                            mode='lines',
                            opacity=0.7,
                            marker={
                                'size': 15,
                                'line': {'width': 0.5, 'color': 'white'}
                            },
                            name='Gas Production'
                        )
                    ],
                    'layout': go.Layout(
                        xaxis={'title': 'Field Days'},
                        yaxis={'title': 'Production (scf/day)'},
                        margin={'l': 60, 'b': 40, 't': 10, 'r': 10},
                        legend={'x': 0, 'y': 1},
                        hovermode='closest'
                    )
                }
            )
        ]),

        html.Div(className="four columns", children=[
            dcc.Graph(
                id='prod-vs-time',
                figure={
                    'data': [
                        go.Scatter(
                            x=tArr,
                            y=qArr,
                            mode='lines',
                            opacity=0.7,
                            marker={
                                'size': 15,
                                'line': {'width': 0.5, 'color': 'white'}
                            },
                            name='Field Production'
                        ),
                        go.Scatter(
                            x=[0, tArr[-1]],
                            y=[params['tgtFlow']*947817.12, params['tgtFlow']*947817.12],
                            mode='lines',
                            opacity=0.7,
                            marker={
                                'size': 15,
                                'line': {'width': 0.5, 'color': 'red'}
                            },
                            name='Target Production'
                        ),
                        go.Scatter(
                            x=tArr,
                            y=numWellArr,
                            mode='lines',
                            opacity=0.7,
                            marker={
                                'size': 15,
                                'line': {'width': 0.5, 'color': 'red'}
                            },
                            name='Well Count',
                            yaxis='y2'
                        )
                    ],
                    'layout': go.Layout(
                        xaxis={'title': 'Field Days'},
                        yaxis={'title': 'Production (scf/day)'},
                        yaxis2={
                            'title': 'Well Count',
                            'overlaying': 'y',
                            'side': 'right'
                        },
                        margin={'l': 60, 'b': 40, 't': 10, 'r': 60},
                        legend={'x': 0, 'y': 1},
                        hovermode='closest'
                    )
                }
            )
        ]),

        html.Div(className="four columns", children=[
            dcc.Graph(
                id='cost-vs-time',
                figure={
                    'data': [
                        go.Scatter(
                            x=tArr,
                            y=expenseArr,
                            mode='lines',
                            opacity=0.7,
                            marker={
                                'size': 15,
                                'line': {'width': 0.5, 'color': 'white'}
                            },
                            name='Total Expenses'
                        ),
                        go.Scatter(
                            x=tArr,
                            y=incomeArr,
                            mode='lines',
                            opacity=0.7,
                            marker={
                                'size': 15,
                                'line': {'width': 0.5, 'color': 'red'}
                            },
                            name='Total Income'
                        ),
                        go.Scatter(
                            x=tArr,
                            y=exposureArr,
                            mode='lines',
                            opacity=0.7,
                            marker={
                                'size': 15,
                                'line': {'width': 0.5, 'color': 'red'}
                            },
                            name='Capital Exposure',
                            yaxis='y2'
                        )
                    ],
                    'layout': go.Layout(
                        xaxis={'title': 'Field Days'},
                        yaxis={'title': 'Cost ($)'},
                        yaxis2={
                            'title': 'Captial Exposure ($)',
                            'overlaying': 'y',
                            'side': 'right'
                        },
                        margin={'l': 60, 'b': 40, 't': 10, 'r': 60},
                        legend={'x': 0, 'y': 1},
                        hovermode='closest'
                    )
                }
            )
        ])
    ]),

    html.Div(className="row", children=[
        html.Div(className="three columns", children=[
            html.H3('Simulation Parameters'),

            html.Div(className="text-center", children=[
                html.Label('Target Flow (TJ/Day)'),
                dcc.Input(value='25.0', type='number', id='inTargetFlow'),

                html.Label('Simulation Time (years)'),
                dcc.Input(value='5', type='number', id='inSimTime'),

                html.Label('Number of Rigs'),
                dcc.Input(value='2', type='number', id='inNumRigs'),

                html.Label('Start Date'),
                dcc.DatePickerSingle(id='inStartDate', date=dt(2018, 7, 2))

            ])
        ]),


        html.Div(className="three columns", children=[
            html.H3('Field Construction Parameters'),

            html.Div(className="text-center", children=[
                html.Label('Well Drilling Time (Days)'),
                dcc.Input(value='30', type='number', id='inDrillTime'),

                html.Label('Time Waiting on Frac (Days)'),
                dcc.Input(value='60', type='number', id='inWaitFracTime'),

                html.Label('Well Frac Time (Days)'),
                dcc.Input(value='10', type='number', id='inFracTime'),

                html.Label('Time Waiting on Piping (Days)'),
                dcc.Input(value='160', type='number', id='inWaitPipeTime')
            ])
        ]),

        html.Div(className="three columns", children=[
            html.H3('Reservoir Parameters'),

            html.Div(className="text-center", children=[
                html.Label('Ave Max Well Flow (Mscf/day)'),
                dcc.Input(value='1.0', type='number', id='inAveFlow'),

                html.Label('Ave Time to 10% Flow (years)'),
                dcc.Input(value='4', type='number', id='inAveDecline')
            ])
        ]),

        html.Div(className="three columns", children=[
            html.H3('Economic Parameters'),

            html.Div(className="text-center", children=[
                html.Label('Gas Price ($USD/GJ)'),
                dcc.Input(value='10.0', type='number', id='inGasPrice'),

                html.Label('Exchange Rate ($AUD/$USD)'),
                dcc.Input(value='1.31', type='number', id='inExchangeRate'),

                html.Label('Cost To Drill ($M)'),
                dcc.Input(value='3.0', type='number', id='inCostToDrill'),

                html.Label('Cost To Frac ($M)'),
                dcc.Input(value='2.0', type='number', id='inCostToFrac'),

                html.Label('Cost To Tie In ($M)'),
                dcc.Input(value='0.5', type='number', id='inCostToTieIn')
            ])
        ])
    ]),

    html.Div(className="row", children=[
        html.H3('Operational Phases')
    ]),

    html.Div(className="phase-container", children=[
        html.Div(className="row", children=[
            html.Div(className="three columns", children=[
                html.H4('Phase 1'),

                html.Label('Phase Start'),
                dcc.DatePickerSingle(id='inPhase1Start', date=dt(2018, 6, 23)),

                html.Label('Number of Rigs'),
                dcc.Input(value='1', type='number', id='inPhase1Rigs'),

                html.Label('Number of Wells'),
                dcc.Input(value='1', type='number', id='inPhase1Wells')
            ]),

            html.Div(className="three columns", children=[
                html.H4('Phase 2'),

                html.Label('Phase Start'),
                dcc.DatePickerSingle(id='inPhase2Start', date=dt(2018, 6, 23)),

                html.Label('Number of Rigs'),
                dcc.Input(value='0', type='number', id='inPhase2Rigs'),

                html.Label('Number of Wells'),
                dcc.Input(value='0', type='number', id='inPhase2Wells')
            ]),

            html.Div(className="three columns", children=[
                html.H4('Phase 3'),

                html.Label('Phase Start'),
                dcc.DatePickerSingle(id='inPhase3Start', date=dt(2018, 6, 23)),

                html.Label('Number of Rigs'),
                dcc.Input(value='0', type='number', id='inPhase3Rigs'),

                html.Label('Number of Wells'),
                dcc.Input(value='0', type='number', id='inPhase3Wells')
            ]),

            html.Div(className="three columns", children=[
                html.H4('Phase 4'),

                html.Label('Phase Start'),
                dcc.DatePickerSingle(id='inPhase4Start', date=dt(2018, 6, 23)),

                html.Label('Number of Rigs'),
                dcc.Input(value='0', type='number', id='inPhase4Rigs'),

                html.Label('Number of Wells'),
                dcc.Input(value='0', type='number', id='inPhase4Wells')
            ])
        ])
    ])
])


@app.callback(dash.dependencies.Output('graphs', component_property='children'),
             [dash.dependencies.Input('inSimTime', 'value'),
             dash.dependencies.Input('inTargetFlow', 'value'),
             dash.dependencies.Input('inNumRigs', 'value'),
             dash.dependencies.Input('inDrillTime', 'value'),
             dash.dependencies.Input('inWaitFracTime', 'value'),
             dash.dependencies.Input('inFracTime', 'value'),
             dash.dependencies.Input('inWaitPipeTime', 'value'),
             dash.dependencies.Input('inAveFlow', 'value'),
             dash.dependencies.Input('inAveDecline', 'value'),
             dash.dependencies.Input('inGasPrice', 'value'),
             dash.dependencies.Input('inExchangeRate', 'value'),
             dash.dependencies.Input('inCostToDrill', 'value'),
             dash.dependencies.Input('inCostToFrac', 'value'),
             dash.dependencies.Input('inCostToTieIn', 'value')
             ])
def update_graph(inSimTime, inTargetFlow, inNumRigs, inDrillTime, inWaitFracTime, inFracTime, inWaitPipeTime, inAveFlow, inAveDecline, inGasPrice, inExchangeRate, inCostToDrill, inCostToFrac, inCostToTieIn):
        params = {
            'simTime': int(inSimTime),
            'tgtFlow': float(inTargetFlow),
            'numRigs': int(inNumRigs),
            'drillTime': int(inDrillTime),
            'fracWaitTime': int(inWaitFracTime),
            'fracTime': int(inFracTime),
            'pipeWaitTime': int(inWaitPipeTime),
            'aveFlow': float(inAveFlow),
            'aveDecline': int(inAveDecline),
            'gasPrice': float(inGasPrice),
            'exchangeRate': float(inExchangeRate),
            'costToDrill': float(inCostToDrill),
            'costToFrac': float(inCostToFrac),
            'costToTieIn': float(inCostToTieIn)
        }

        tArr, qArr, expenseArr, incomeArr, decArr, exposureArr, numWellArr = simulateField(params)

        return [
        html.Div(className="four columns", children=[
            dcc.Graph(
                id='decline-vs-time',
                figure={
                    'data': [
                        go.Scatter(
                            x=tArr,
                            y=decArr,
                            mode='lines',
                            opacity=0.7,
                            marker={
                                'size': 15,
                                'line': {'width': 0.5, 'color': 'white'}
                            },
                            name='Gas Production'
                        )
                    ],
                    'layout': go.Layout(
                        xaxis={'title': 'Field Days'},
                        yaxis={'title': 'Production (scf/day)'},
                        margin={'l': 60, 'b': 40, 't': 10, 'r': 10},
                        legend={'x': 0, 'y': 1},
                        hovermode='closest'
                    )
                }
            )
        ]),

        html.Div(className="four columns", children=[
            dcc.Graph(
                id='prod-vs-time',
                figure={
                    'data': [
                        go.Scatter(
                            x=tArr,
                            y=qArr,
                            mode='lines',
                            opacity=0.7,
                            marker={
                                'size': 15,
                                'line': {'width': 0.5, 'color': 'white'}
                            },
                            name='Field Production'
                        ),
                        go.Scatter(
                            x=[0, tArr[-1]],
                            y=[params['tgtFlow']*947817.12, params['tgtFlow']*947817.12],
                            mode='lines',
                            opacity=0.7,
                            marker={
                                'size': 15,
                                'line': {'width': 0.5, 'color': 'red'}
                            },
                            name='Target Production'
                        ),
                        go.Scatter(
                            x=tArr,
                            y=numWellArr,
                            mode='lines',
                            opacity=0.7,
                            marker={
                                'size': 15,
                                'line': {'width': 0.5, 'color': 'red'}
                            },
                            name='Well Count',
                            yaxis='y2'
                        )
                    ],
                    'layout': go.Layout(
                        xaxis={'title': 'Field Days'},
                        yaxis={'title': 'Production (scf/day)'},
                        yaxis2={
                            'title': 'Well Count',
                            'overlaying': 'y',
                            'side': 'right'
                        },
                        margin={'l': 60, 'b': 40, 't': 10, 'r': 60},
                        legend={'x': 0, 'y': 1},
                        hovermode='closest'
                    )
                }
            )
        ]),

        html.Div(className="four columns", children=[
            dcc.Graph(
                id='cost-vs-time',
                figure={
                    'data': [
                        go.Scatter(
                            x=tArr,
                            y=expenseArr,
                            mode='lines',
                            opacity=0.7,
                            marker={
                                'size': 15,
                                'line': {'width': 0.5, 'color': 'white'}
                            },
                            name='Total Expenses'
                        ),
                        go.Scatter(
                            x=tArr,
                            y=incomeArr,
                            mode='lines',
                            opacity=0.7,
                            marker={
                                'size': 15,
                                'line': {'width': 0.5, 'color': 'red'}
                            },
                            name='Total Income'
                        ),
                        go.Scatter(
                            x=tArr,
                            y=exposureArr,
                            mode='lines',
                            opacity=0.7,
                            marker={
                                'size': 15,
                                'line': {'width': 0.5, 'color': 'red'}
                            },
                            name='Capital Exposure',
                            yaxis='y2'
                        )
                    ],
                    'layout': go.Layout(
                        xaxis={'title': 'Field Days'},
                        yaxis={'title': 'Cost ($)'},
                        yaxis2={
                            'title': 'Captial Exposure ($)',
                            'overlaying': 'y',
                            'side': 'right'
                        },
                        margin={'l': 60, 'b': 40, 't': 10, 'r': 60},
                        legend={'x': 0, 'y': 1},
                        hovermode='closest'
                    )
                }
            )
        ])
        ]

# @app.callback(dash.dependencies.Output('phase-meta-container', component_property='children'),
#              [dash.dependencies.Input('inNumPhases', 'value')])
# def update_phases(inNumPhases):
#         html.Div(className="phase-container", children=[
#             html.Div(className="row", children=[
#                 html.Div(className="three columns", children=[
#                     html.Label('Phase Start'),
#                     dcc.DatePickerSingle(id='inPhaseStart', date=dt(2018, 6, 23))
#                 ]),
#                 html.Div(className="three columns", children=[
#                     html.Label('Number of Rigs'),
#                     dcc.Input(value='1', type='number', id='inNumRigs')
#                 ])
#             ])
#          ])


if __name__ == '__main__':
    app.run_server(debug=True)
