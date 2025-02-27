import dash #combo of flask, react.js, plotly.js
from dash import dcc, html # create interactive components, access HTML tags
import dash_bootstrap_components as dbc
# import dash_core_components as dcc #  create interactive components
# import dash_html_components as html #access HTML tags
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import covasim as cv
cv.options.set(dpi=300, show=False, close=True, verbose=0)
import pandas as pd
import numpy as np
from numpy import mean
from helper_stats import *



# ------------- initializing app -------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "COVID-19 Event Simulator"
server = app.server

# ------------- app input functions and values -------------
state_names = ["USA","Alaska", "Alabama", "Arkansas", "Arizona", "California", "Colorado", "Connecticut", "District of Columbia", "Delaware", "Florida", "Georgia", "Hawaii", "Iowa", "Idaho", "Illinois", "Indiana", "Kansas", "Kentucky", "Louisiana", "Massachusetts", "Maryland", "Maine", "Michigan", "Minnesota", "Missouri", "Mississippi", "Montana", "North Carolina", "North Dakota", "Nebraska", "New Hampshire", "New Jersey", "New Mexico", "Nevada", "New York", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Puerto Rico", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Virginia", "Vermont", "Washington", "Wisconsin", "West Virginia", "Wyoming"]
event_settings = ["Indoor", "Outdoor"]
vax_options = [ "Default (assumes regional prevalence)", "Mandatory Vaccination", "No Vaccination"]
testing_options = ["No Testing", "Entry antigen", "Daily antigen", "PCR 2-day", "PCR 4-day"]
variants = ["Omicron (4.92x)", "Less transmissible (0.5x)", "Original strain (1x)", "Alpha (1.5x)", "Delta (2.4x)", "More transmissible (10x)"]
variant_mapping = {
    "Omicron (4.92x)":4.92, 
    "Less transmissible (0.5x)":0.5, 
    "Original strain (1x)":1.0, 
    "Alpha (1.5x)":1.5, 
    "Delta (2.4x)":2.4, 
    "More transmissible (10x)":10
}
def OptionMenu(values, label, options=None, instructions=None, **kwargs):
    if not options:
        options = [{"label": s, "value": s} for s in values]
    # kwargs["value"] = kwargs.get("value", values[0]) #if you want a default value
    if len(options) <= 4:
        component = dbc.RadioItems
        kwargs["inline"] = True
    else:
        component = dbc.Select
    return dbc.FormGroup([dbc.Label(label),component(options=options, **kwargs), dbc.FormText(instructions)])

def NumberInput(id_name, minval=1, maxval=7, label_text = None, instructions = None):
    # number_input = html.Div(
    # [
    #     html.P("Event Duration (Days)"),
    #     dbc.Input(type="number", min=0, max=10, step=1),
    # ],
    # id="styled-numeric-input",
    # )
    text_input = dbc.FormGroup(
        [
            dbc.Label(label_text),
            # dbc.Input(placeholder="Input goes here...", type="text"),
            dbc.Input(id = id_name, type="number", min=minval, max=maxval, step=1),
            dbc.FormText(instructions),
        ]
    )

    return text_input

def SwitchInput():
    switches = dbc.FormGroup(
        [
            dbc.Label("Non-Pharmaceutical Interventions"),
            dbc.Checklist(
                options=[
                    {"label": "Mask wearing", "value": 1},
                    # {"label": "Event capacity reduction", "value": 2},
                    # {"label": "Improved ventilation indoors", "value": 3},
                    # {"label": "Disabled Option", "value": 3, "disabled": True},
                ],
                value=[],
                id="npis",
                switch=True,
            ),
        ]
    )
    return switches

def CustomSlider(label, marks, set_val, instructions, minval, maxval, **kwargs):
    return dbc.FormGroup(
        [
            dbc.Label(label),
            dcc.Slider(
                    min=minval,
                    max=maxval,
                    step=None,
                    marks=marks,
                    value=set_val,
                    **kwargs
            ),
            dbc.FormText(instructions),

        ]
    )

# ------------- vax and testing simulation functions -------------
"""
Function: test_intervention - creates intervention for a testing strategy
Note: this only works for cases generated at event 

To-Do
---------
For testing, esp daily antigen, shouldnt the days_testing argument = 1, instead of 0. We can specify an end date to ensure that testing stops on day 1? 
See documentation: # https://docs.idmod.org/projects/covasim/en/latest/covasim.interventions.html?highlight=test_num#covasim.interventions.test_num

Parameters
----------
test_del: Delay in test result
days_testing: Number of days in event testing susceptibles
subtarg: Indices of population to subtarget
sens: Sensitivity of test used

""" 


def test_intervention(test_del, days_testing, rapid, window, pars, incidence_avg, sens, subtarg=None):
    if (rapid):
        pars['pop_infected'] -= sens * pars['pop_infected']
    else:
        # note: 11/6 removing underep factor as this has been taken into account for both usa and state
        num_preinfectious = sum([((1/window) * pars['pop_size'] * incidence_avg * x) for x in range(1,window+1)])
        
        # old preinfections
        # Newly infected are those infected after test (assume even distribution of test date from 1 to 'window' days ago)
        # Assume 12 days infectious, all tests within 4.6 day period from exposed->infectious (max window 4)
        # These people will test negative even with a perfect test, because they were exposed after testing negative
        # num_preinfectious = prevalence * pars['pop_size'] * sum([x*(1/(12*window)) for x in range(1,window+1)])
        
        # Finally, remove population that is detected by the reported tests
        pars['pop_infected'] += num_preinfectious - sens * pars['pop_infected']
        
    return cv.test_num(daily_tests=pars['pop_size']*days_testing, 
                       start_day=pars['start_day'], 
                       subtarget=subtarg,
                       symp_test=0,
                       sensitivity=sens,
                       test_delay=test_del), pars

"""
Function: vaccine_intervention: Creates intervention for a vaccine-based entry strategy. returns intervention

To-Do
---------
Check Cumulative infections for mandatory vaxing - values seem way too high?

Parameters
----------
percent_vax: Percentage of overall population vaccinated
passport: If true, 100% of attendees must be vaccinated
efficacy_inf: Efficacy against infection
efficacy_symp: Efficacy against symptoms 
"""


def vaccine_intervention(percent_vax,efficacy_inf, immune_esc, efficacy_symp, pars, passport = False):
    if passport:
        percent_vax = 1
    efficacy_inf_updated = 1-((1-efficacy_inf) * (1-immune_esc))
    pars['pop_infected'] -= (1-efficacy_inf_updated) * percent_vax * pars['pop_infected']
    return cv.simple_vaccine(days=0, prob=percent_vax, rel_sus=efficacy_inf_updated, rel_symp=efficacy_symp), pars

# ------------- Import state & us level data: new cases, total cases, percent vaccinated -------------
# State daily data  
can_state = pd.read_csv("states.csv")

# USA timeseries data 
can_usa_timeseries = pd.read_csv("UStimeseries.csv")
# can_usa_timeseries.dropna(subset = ['actuals.cases'], inplace=True)  # no longer using this data
# can_usa_timeseries.dropna(subset = ['metrics.vaccinationsCompletedRatio'], inplace=True)  # no longer using this data
can_usa_timeseries['date']=pd.to_datetime(can_usa_timeseries.date)
can_usa_timeseries.sort_values(by='date', inplace=True)

# State timeseries data  - covidact now data [replaced with covidestim data (below) on 10/20]
# can_state_timeseries = pd.read_csv("statestimeseries.csv")
# can_state_timeseries.dropna(subset = ['actuals.cases'], inplace=True)
# can_state_timeseries['date']=pd.to_datetime(can_state_timeseries.date)
# can_state_timeseries.sort_values(by='date', inplace=True)

# state timeseries - covidestim data
cest_state_timeseries = pd.read_csv("covidestim_estimates.csv")
cest_state_timeseries.dropna(subset = ['infections'], inplace=True)
cest_state_timeseries['date']=pd.to_datetime(cest_state_timeseries['date'])
cest_state_timeseries.sort_values(by='date', inplace=True)




# ------------- Build component parts -------------
# avp_graph = dcc.Graph(id="avp_graph", style={"height": "500px"})
# loc_graph = dcc.Graph(id="loc_graph", style={"height": "500px"})
# div_alert = dbc.Spinner(html.Div(id="alert-msg"))


controls = [
    dbc.Alert("Basic Information", color="primary"),
    # dbc.Alert(
    #     [
    #         html.H5("Basic Information", className="alert-heading"),
    #         # html.P(
    #         #     "This is a success alert with loads of extra text in it. So much "
    #         #     "that you can see how spacing within an alert works with this "
    #         #     "kind of content."
    #         # ),
    #         html.Hr(),
    #         html.P(
    #             "Fill out the event details to estimate the COVID risk.",
    #             className="mb-0",
    #         ),
    #     ],
    #     color="primary",
    # ),
    OptionMenu(id="location", label="Location", values=state_names, placeholder="Select Country or U.S. State"),
    NumberInput(id_name= "event_duration", minval=1, maxval=7, label_text="Event Duration", instructions = "Choose between 1-7 days"),
    NumberInput(id_name="num_people", minval=10, maxval=100000, label_text="Number of Participants",instructions = "Choose between 10-10,000 participants*"),
    OptionMenu(id="event_setting", label="Event Setting", values=event_settings, value=event_settings[0]),
    OptionMenu(id="test_setting", label="Testing Options", values=testing_options, placeholder="Select Testing"),
    OptionMenu(id="vax_setting", label="Vaccination Requirements", values=vax_options, value=vax_options[0]),
    SwitchInput(),
    html.P(" "),
    dbc.Alert("Additional Modifiers", color="primary"),
    CustomSlider(
        id="num_contacts",
        label="Number of Daily Close Contacts",
        marks={20:'20', 20:'20', 40:'40', 60:'60', 80:'80', 100:'100'},
        set_val = 20,
        instructions = "Choose the average number of close contacts per person attending the event.",
        minval = 20, 
        maxval = 100,
    ),
    CustomSlider(
        id="prevalence_mod",
        label="Prevalence Modifier",
        marks={0.5: '0.5x', 1: '1x', 1.5: '1.5x',2: '2x'},
        set_val = 1,
        instructions = "Choose a prevalence modifier to see the impacts of increased or decreased caseloads in your region.",
        minval = 0.5, 
        maxval = 2
    ),
    OptionMenu(id="variant_trans_value", label="Variant Transmissibility", values=variants, value=variants[0], placeholder="Select Variant", instructions="The default variant can be changed to see the impacts of increased or decreased transmissibility for your event."),
    CustomSlider(
        id="immune_escape",
        label="Immune Escape (%)",
        marks={0: '0', 10: '10', 20: '20', 30: '30', 40: '40', 50: '50', 60: '60', 70: '70', 80: '80', 90: '90', 100: '100'},
        set_val = 0,
        instructions = "Select immune escape %.",
        minval = 0, 
        maxval = 100,
        # tooltip={"placement": "bottom", "always_visible": True}
    ),
    dbc.Button("Run Simulation", color="primary", id="button-train", n_clicks=0),
    html.P(" "),
    html.P("*Contact us to run simulations for events larger than 10,000 people.")
    # dbc.Spinner(children=[avp_graph]),
    # dbc.Spinner(html.Div(id="loading-output")),
]

# interventions = [
#     OptionMenu(id="purpose", label="Purpose", values=purposes),
#     dbc.Button("Run Simulation", color="primary", id="button-train"),
# ]


# ------------- define app layout -------------
app.layout = dbc.Container(
    fluid=True,
    children=[
        html.H1("COVID-19 Event Safety Modeling"),
        html.Hr(),
        # dbc.Row(dbc.Col(html.Div("Intro info can go here!"))),
        dbc.Row(dbc.Col(
            html.Div([
                # html.H2('Hello Dash'),
                html.Div([
                    html.P(["This tool helps you estimate the COVID risk of holding in-person events and find effective safety measures for minimizing transmission. Generally, you can make an event safer by requiring vaccination, testing participants, gathering outside, reducing event capacity, increasing ventilation, and/or requiring masks. For example, you can simulate hosting your event in North Carolina requiring masks or in North Dakota requiring vaccines. Our methods can be found ",  html.A("here", href="")," and all models were run using ", html.A("Covasim", href="http://paper.covasim.org"), ". Population, incidence, prevalence, and contact matrices are based on state-level data."]),
                    # html.P("This conversion happens behind the scenes by Dash's JavaScript front-end")
                ])
            ])
        )),
        dbc.Row(
            [
                dbc.Col([dbc.Card(controls, body=True)], md=3),
                dbc.Col(dbc.Spinner(children=[dcc.Graph(id="avp_graph", style={"height": "500px"})], size="sm", color="primary")),
                dbc.Col(dbc.Spinner(children=[dcc.Graph(id="loc_graph", style={"height": "500px"})], size="sm", color="primary")),
                # dbc.Col([avp_graph]),
                # dbc.Col([loc_graph]),
                # dbc.Col(dcc.Graph(id="coef-graph", style={"height": "800px"}), md=5),
            ]
        ),
        # dbc.Row(
        #     [
        #         dbc.Col(dbc.Button("Save Simulation", color="primary", id="button-save", n_clicks=0), width=4),
        #     ],
        #     justify="center",
        # ),
        # dbc.Row(
        #     [
        #         dbc.Col(html.Div(""), md=3),
        #         dbc.Col([loc_graph], md=5),
        #         # dbc.Col([avp_graph, query_card], md=4),
        #         # dbc.Col(dcc.Graph(id="coef-graph", style={"height": "800px"}), md=5),
        #     ] #,
        #     # justify="center",
        # ),
    ],
    style={"margin": "auto"},
)

# ------------- Define callbacks -------------
@app.callback(
    # [
        # Output("alert-msg", "children"),
        # Output("loading-output", "children"),
        Output("avp_graph", "figure"),
        Output("loc_graph", "figure"),
        # Output("sql-query", "children"),
    # ],
    [Input("button-train", "n_clicks")],
    [
        State("location", "value"),
        State("event_duration", "value"),
        State("num_people", "value"),
        State("event_setting", "value"),
        State("test_setting", "value"),
        State("vax_setting", "value"),
        State("npis", "value"),
        State("num_contacts", "value"),
        State("prevalence_mod", "value"),
        State("variant_trans_value", "value"),
        State("immune_escape", "value"),
    ],
)

def run_sim(n_clicks, location, event_duration, num_people, event_setting, test_setting, vax_setting, npi, num_contacts, prevalence_mod, variant_trans_value, immune_escape):
# def run_sim(event_duration, num_people, location, event_environment=None, mask_wearing=False, test_type=None, use_vaccines=True, mandatory_vax=False):    
    if n_clicks < 1: 
        avp_fig = go.Figure()
        return avp_fig, avp_fig
    if num_people > 10000:
        avp_fig = go.Figure()
        return avp_fig, avp_fig
    if event_duration > 7:
        avp_fig = go.Figure()
        return avp_fig, avp_fig
    # ----- basic event characteristics ----- 
    event_duration = event_duration if event_duration != None else 1 #temp fix for misfiring nclicks
    num_people = num_people if num_people != None else 1
    covsim_location = "USA-" + location if location != "USA" else "USA"
    event_environment= None if event_setting == "Mixed" else event_setting
    test_type= None if test_setting == "No Testing" else test_setting
    use_vaccines=False if vax_setting == "No Vaccination" else True
    mandatory_vax=True if vax_setting == "Mandatory Vaccination" else False
    mask_wearing = True if 1 in npi else False
    # print(prevalence_mod, event_setting)
    # print(vax_setting, use_vaccines)
    # print(npi)
    # print("test_setting: ", test_setting)
    # print("vax_setting: ", vax_setting)
    # print("event_environment:", event_environment, 
    # "test_type:", test_type, "use_vaccines:", use_vaccines, "mandatory_vax:", mandatory_vax)

    # ---------- Point estimates ---------- 
    # indoor_factor =  9.35 - removed as indoor is now default
    outdoor_factor = 0.055 #.11 
    mask_factor = .56
    ventilation_factor = .69
    capacity_factor = .5
    start_day = '2021-07-01' # default start date
    variant_transmissibility = variant_mapping[variant_trans_value] #2.4 - delta variant

    # location-specific & other characteristics
    #under_rep_factor = 4.2 #source: CDC feb 2022 - no longer being used
    location_pop = population_dict[location]
    
    state_abv = us_state_abbrev[location]
    if state_abv == 'USA':
        # old calculations based on us time series and under reporting factor
        # location_total_inf = can_usa_timeseries.iloc[-1]['actuals.cases']
        # location_cases_d10 = sum(can_usa_timeseries.iloc[range(-10,0,1)]['actuals.newCases'].values)
        # incidence_avg = (mean(can_usa_timeseries.iloc[range(-7,0,1)]['actuals.newCases'].values)*under_rep_factor)/location_pop # avg new cases last 7 days divided by population, 11/8: accounted for under-reporting
        
        # infections total - total of sum
        location_total_inf = cest_state_timeseries['infections'].sum()
        #  last 10 dates
        l10_dates = cest_state_timeseries.date.unique()[-10::1]
        # calculate total daily infections for each of the last 10 dates
        daily_infections_l10 = []
        for date_val in l10_dates:
            daily_infections_l10.append(cest_state_timeseries[cest_state_timeseries['date']==date_val]['infections'].sum())
        location_cases_d10 = sum(daily_infections_l10)
        incidence_avg = np.mean(daily_infections_l10[-7::])/location_pop # mean of last 7 total daily infections
        perc_vax = can_usa_timeseries.iloc[-1]['metrics.vaccinationsCompletedRatio'] # TODO(bugfix): this fails if last column value is NaN, should we specify last non-NaN value?
    else:
        location_total_inf = cest_state_timeseries[cest_state_timeseries['state']==location]['infections'].sum()
        location_cases_d10 = cest_state_timeseries[cest_state_timeseries['state']==location].iloc[range(-10,0,1)]['infections'].sum()
        incidence_avg = cest_state_timeseries[cest_state_timeseries['state']==location].iloc[range(-7,0,1)]['infections'].mean()/location_pop
        perc_vax = can_state[can_state['state']==state_abv]['metrics.vaccinationsCompletedRatio'].values[0] # TODO(bugfix): this data does not exist for HI, DC, NH
    
    # calculate location specific prevelance
    prevalence = ((location_cases_d10)/location_pop)*prevalence_mod

    # update immune escape value
    immune_escape = immune_escape/100

    # calculate location specific susceptibility proportion (0.747 - old number)
    susceptibility_proportion = 1-((location_total_inf)/location_pop) #no need for under-rep factor for state level data as we are looking @ total infections
    # update susceptibility_proportion with immune escape
    susceptibility_proportion = 1-((1-susceptibility_proportion) * (1-immune_escape))
    #   print("location: {}, location abv: {}".format(location, state_abv))
    #   print("location_total_inf: {}, location_cases_d10: {}, perc_vax: {}".format(location_total_inf, location_cases_d10, perc_vax))
    
    # vaccination levels:
    v_efficacy_inf = .1 # Vax efficacy against infection (e.g .2 == 80% efficacy)
    v_efficacy_symp = .06 # Vax efficacy against symptoms
    
    # ---------- Define parameters in covasim format ---------- 
    pars = dict(
        pop_type = 'hybrid', # Use a more realistic population model
        pop_size = num_people,
        pop_infected = num_people*prevalence if num_people*prevalence > 1 else 1,
        start_day = start_day,
        n_days = event_duration,
        location = covsim_location # Case insensitive
    )
    
    # ----------  model changes (variants, environment, NPIs, testing, vaccines) to beta on day 0 ---------- 
    all_interventions = []
    
    # variant transmissibility
    variant_trans = cv.change_beta(0, variant_transmissibility*susceptibility_proportion)
    all_interventions.append(variant_trans)
    
    # environment
    # if event_environment == "Indoor":
    #     environment = cv.change_beta(0, indoor_factor)
    #     all_interventions.append(environment)
    if event_environment == "Outdoor":
        environment = cv.change_beta(0, outdoor_factor)
        all_interventions.append(environment)

    # changing number of contacts
    if num_contacts != 20: #if not default
        change_num_contacts = cv.change_beta(0, num_contacts/20) # change by a factor relative to default
        all_interventions.append(change_num_contacts)          
    
    # mask wearing
    if mask_wearing:
        masks = cv.change_beta(0, mask_factor)
        all_interventions.append(masks)   
    
    # testing 
    """
    -   test_del: Delay in test result
    -   days_testing: Number of days in event testing susceptibles
    -   subtarg: Indices of population to subtarget
    -   sens: Sensitivity of test used
    """
 
    testing_scenarios = {
        # format = [test_del, days_testing, rapid, window]
        "Entry antigen":[0,0,False,3,0.945], # add 3 days to window for antigen tests (since 3.5 is not possible)
        "Daily antigen": [0,event_duration,False,3,0.945], #[0,7,True,0] # add 3 days to window for antigen tests (since 3.5 is not possible)
        "PCR 2-day":[0,0,False,5,1], # add 3 days to window for PCR tests
        "PCR 4-day":[0,0,False,7,1], # add 3 days to window for PCR tests        
    } 
    subtarg = None # Subtargetting of tests
    #sens = .984 # Sensitivity of test used - commented out since sensitivity is different for different tests
    if test_type != None:
        test_int, pars = test_intervention(test_del=testing_scenarios[test_type][0], 
                                           days_testing=testing_scenarios[test_type][1], 
                                           rapid=testing_scenarios[test_type][2], 
                                           window=testing_scenarios[test_type][3], 
                                           pars=pars,
                                           incidence_avg=incidence_avg,
                                           sens=testing_scenarios[test_type][4])
        all_interventions.append(test_int)
        
    
    # vaccinations - assumes state level vax numbers (default), unless otherwise specified (either mandatory vax, or no vax)
    passport = mandatory_vax # True if 100% of attendees must be vaccinated
    if use_vaccines:
        vc, pars = vaccine_intervention(perc_vax, v_efficacy_inf, immune_escape, v_efficacy_symp, pars, passport)
        all_interventions.append(vc)

    
    # ---------- run simulation ----------
    # print("Running SIMULATION")
    sim = cv.Sim(pars, interventions = all_interventions)
    msim = cv.MultiSim(sim)
    msim.run(n_runs=10)
    msim.mean()
    # msim.plot(to_plot=['new_infections', 'cum_infections'])
    sim_json = msim.to_json()

    # ---------- plotting ----------
    df_new_infections = pd.DataFrame(list(zip(sim_json['results']['t'], 
                            sim_json['results']['new_infections'],
                            sim_json['results']['new_infections_low'],
                            sim_json['results']['new_infections_high'])),
                    columns =['dates','new_infections', 'new_infections_low', 'new_infections_high'])
    
    df_cum_infections = pd.DataFrame(list(zip(sim_json['results']['t'], 
                            sim_json['results']['cum_infections'],
                            sim_json['results']['cum_infections_low'],
                            sim_json['results']['cum_infections_high'])),
                    columns =['dates','cum_infections', 'cum_infections_low', 'cum_infections_high'])

    df_new_infections[df_new_infections < 0] = 0
    df_cum_infections[df_cum_infections < 0] = 0


    avp_fig = go.Figure([
        go.Scatter(
            x=df_new_infections['dates'].tolist(),
            y=df_new_infections['new_infections'].tolist(),
            line=dict(color='rgb(0,100,80)'),
            mode='lines',
            name="Estimated New Cases",
            showlegend=True
        ),
        go.Scatter(
            x=df_new_infections['dates'].tolist()+df_new_infections['dates'].tolist()[::-1], # x, then x reversed
            y=df_new_infections['new_infections_high'].tolist()+df_new_infections['new_infections_low'].tolist()[::-1], # upper, then lower reversed
            fill='toself',
            fillcolor='rgba(0,100,80,0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            hoverinfo="skip",
            showlegend=True,
            name = 'Confidence Band'
        )
    ])
    #  https://stackoverflow.com/questions/55704058/plotly-how-to-set-the-range-of-the-y-axis
    avp_fig.update_layout(yaxis_range=[-0.01,max(max(df_new_infections['new_infections_high'].tolist()), 8)+2],
    xaxis_range=[1,event_duration],
    yaxis_title='Cases',
    xaxis_title='Day',
    title_text='New Daily Infections', title_x=0.5, title_y=0.875,
    hovermode="x",
    xaxis = dict(dtick = 1),
    showlegend=True,
    legend=dict(yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01)
    )


    # find value for min cumulative infections on day 0
    min_cum_infections = df_cum_infections[df_cum_infections['dates'] == 0]["cum_infections_low"].values[0]

    # replace any values on the lower CI that fall below min_cum_infections
    df_cum_infections.loc[df_cum_infections['cum_infections_low'] < min_cum_infections, "cum_infections_low"] = min_cum_infections

    cum_infections_high = df_cum_infections['cum_infections_high'].tolist()
    cum_infections = df_cum_infections['cum_infections'].tolist()
    loc_fig = go.Figure([
        go.Scatter(
            x=df_cum_infections['dates'].tolist(),
            y=df_cum_infections['cum_infections'].tolist(),
            line=dict(color='rgb(0,100,80)'),
            mode='lines',
            name="Estimated Total Cases",
            showlegend=True
        ),
        go.Scatter(
            x=df_cum_infections['dates'].tolist()+df_cum_infections['dates'].tolist()[::-1], # x, then x reversed
            y=df_cum_infections['cum_infections_high'].tolist()+df_cum_infections['cum_infections_low'].tolist()[::-1], # upper, then lower reversed
            fill='toself',
            fillcolor='rgba(0,100,80,0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            hoverinfo="skip",
            name = 'Confidence Band',
            showlegend=True
        
        )
    ])
    loc_fig.update_layout(
    yaxis_range=[-0.01,max(max(cum_infections_high), 8)+5],
    xaxis_range=[1,event_duration],
    yaxis_title='Cases',
    xaxis_title='Day',
    title_text='Cumulative Infections', title_x=0.5, title_y=0.875,
    hovermode="x",
    xaxis = dict(dtick = 1),
    showlegend=True,
    legend=dict(yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01)
    )
    # avp_fig.show()
    # loc_fig.show()
    return avp_fig, loc_fig

# if __name__ == "__main__":
#     app.run_server(debug=True)
