"""
General description:
---------------------
contributors:
    Qing Du
    Carina Geyer
    Carsten Hammer

Installation requirements:
---------------------------
This example requires oemof 0.2.2. Install by:

    pip install oemof==0.2.2

"""

# Default logger of oemof
#from oemof.tools import logger
#from oemof.tools import helpers
import oemof.solph as solph
from oemof.tools import economics

# import oemof base classes to create energy system objects
#import logging
import os
import pandas as pd
#import warnings

#from oemof import solph
from oemof.outputlib import processing

from oemof.outputlib import views

import source_x_system as es
#import os

#import pandas as pd

#import oemof.graph as grph 
import pprint as pp

import matplotlib.pyplot as plt 



""" Reference Network """


solver = 'cbc'  # 'glpk', 'gurobi',....
debug = False  # Set number_of_timesteps to 3 to get a readable lp-file.
solver_verbose = False  # show/hide solver output


#data
#capex,wacc,n,capacity per pp : Stromgestehungskosten Erneuerbare Energien, ISE, März 2018
#wind and pv feed in and electricity demand : 
#fuelprices & development : Prognos AG 2013; Hecking et al. 2017; Schlesinger et al. 2014; World Bank 2017; DLR Rheinland-Pfalz 2017; Scheftelowitz et al. 2016
#efficiency : Wietschel et al. 2010

date_time_index = pd.date_range('1/1/2050', periods = 8760, freq = 'H' )
   
energysystem = solph.EnergySystem(timeindex=date_time_index)

#input_data

filename = os.path.join(os.path.dirname(__file__), 'normalised data.csv')
data = pd.read_csv(filename)

# do not change!
sum_nominal_load_values = 6348.4153 # fixed value of the normalized el_demand series


# use the choosen variable for the actuel value in the network SINK
nominal_BAU = 506000000/sum_nominal_load_values # traffic and heat 
# investment for each energy carrier
variable_costs_x = 1000000
epc_x            = economics.annuity(capex =10000000000000000, n=30, wacc=0.5)


epc_wind_on     = economics.annuity(capex =1780000, n=25, wacc=0.025)

epc_wind_off    = economics.annuity(capex =4000000, n=25, wacc=0.048)

epc_pv_Si       = economics.annuity(capex=717500, n=25, wacc=0.021)
epc_pv_thin     = economics.annuity(capex = 800000, n=25, wacc=0.021)


# MAXIMUM Capacity
   
max_pv_Si   = 163026*0.5 # 220000  
max_pv_CIGS = 27500
max_pv_CdTe = 27500
       
max_wind_on_hybrid    = 593920
max_wind_on_asynchron = 593920
       
max_wind_off_pure = 0.5 * 45000    

###########
# 2 Built the network
##########

bel = solph.Bus(label = "electricity")
b_wind_off = solph.Bus(label = 'electricity_wind_off')
b_pv = solph.Bus(label = 'electricity_pv')
# add all Buses to the EnergySystem
energysystem.add(bel)
energysystem.add(b_wind_off)
energysystem.add(b_pv)
#####################################Sources##################################
# source X
energysystem.add(solph.Source(label='rx', 
  outputs={bel: solph.Flow(nominal_value = None,
   variable_costs = variable_costs_x,
   investment = solph.Investment(ep_costs=epc_x))}))

   
# source wind onshore
energysystem.add(solph.Source(label='wind_on_hybrid', 
    outputs={bel: solph.Flow(fixed=True, 
    actual_value=data['Wind_on'], 
    investment = solph.Investment(ep_costs=epc_wind_on, 
    maximum=max_wind_on_hybrid))}))
    
energysystem.add(solph.Source(label='wind_on_asynchron',
    outputs={bel: solph.Flow(fixed=True, 
    actual_value=data['Wind_on'], 
    investment = solph.Investment(ep_costs=epc_wind_on,
    maximum=max_wind_on_asynchron))}))
    
 
#source wind offshore 
energysystem.add(solph.Source(label='wind_off_pure', 
    outputs={b_wind_off: solph.Flow(fixed=True, 
    actual_value=data['Wind_off'], 
    investment = solph.Investment(ep_costs=epc_wind_off,
    maximum=max_wind_off_pure))}))
  
    
#connection wind off electricity excess and b electricity

energysystem.add(solph.Transformer(
    label="t_wind_off",
    inputs={b_wind_off: solph.Flow()},
    outputs={bel: solph.Flow()},
    conversion_factors={bel: 1}))

# source pv  
energysystem.add(solph.Source(label='pv_Si', 
    outputs={b_pv: solph.Flow(fixed=True, 
    actual_value=data['PV'],
    investment = solph.Investment(ep_costs=epc_pv_Si,maximum=max_pv_Si))}))
    
energysystem.add(solph.Source(label='pv_CIGS', 
    outputs={b_pv: solph.Flow(fixed=True, 
    actual_value=data['PV'], 
    investment = solph.Investment(ep_costs=epc_pv_thin,maximum=max_pv_CIGS))}))

energysystem.add(solph.Source(label='pv_CdTe', 
    outputs={b_pv: solph.Flow(fixed=True, 
    actual_value=data['PV'], 
    investment = solph.Investment(ep_costs=epc_pv_thin,maximum=max_pv_CdTe))}))

energysystem.add(solph.Transformer(
    label="t_pv",
    inputs={b_pv: solph.Flow()},
    outputs={bel: solph.Flow()},
    conversion_factors={bel: 1}))   
####################################SINK######################################
energysystem.add(solph.Sink(label='demand_elec', 
    inputs={bel: solph.Flow(
    actual_value=data ['normalised_load_profile'] , fixed=True, 
    nominal_value= nominal_BAU)}))

energysystem.add(solph.Sink(label = 'electricity_excess', 
    inputs={b_wind_off:solph.Flow(variable_costs = 1.391, nomial_value = 22500)}))
   
energysystem.add(solph.Sink(label = 'electricity_excess_1', 
    inputs={b_pv:solph.Flow(nominal_value = 55000)})) 
################################Storage########################################
energysystem.add(solph.components.GenericStorage(label='storage',
    inputs={bel: solph.Flow()},
    outputs={bel: solph.Flow()},
    nominal_capacity = 129100,
    inflow_conversion_factor=1, outflow_conversion_factor=1))

############END OF NETWORK#####################################################

####################Start of Optimization and data collecting ################
      
om = solph.Model(energysystem)
om.solve(solver = 'cbc', solve_kwargs ={'tee':True})
        
energysystem.results['main'] = processing.results(om)
energysystem.results['meta'] = processing.meta_results(om)
#
energysystem.dump(dpath=None, filename=None)
    # define an alias for shorter calls below (optional)

results = energysystem.results['main']

# define an alias for shorter calls below (optional)
#results_capacity = energysystem.results['main']

electricity_bus    = views.node(results, 'electricity')
wind_off_bus       = views.node(results, 'electricity_wind_off')
pv_bus             = views.node(results, 'electricity_pv')

sourceX            = views.node(results, 'rx')
wind_on_hydprid    = views.node(results, 'wind_on_hypride')
wind_on_asynchron  = views.node(results, 'wind_on_asynchron')
wind_on_pure       = views.node(results, 'wind_on_pure')

pv_Si              = views.node(results, 'pv_Si')
pv_CIGS            = views.node(results, 'pv_CIGS')
pv_CdTe            = views.node(results, 'pv_CdTe')

storage            = views.node(results, 'storage')
electricty_excess  = views.node (results, 'electricity_excess') 



######## create different Data Frame for the different scearnaios#############
############create excel file of max. capacites of each technology############

mbc= processing.create_dataframe(om)


fn = os.path.join(os.path.dirname(__file__), 'source_x_dataframe.xlsx')
pd.DataFrame(mbc).to_excel(fn)

#1 get the maximum capacities of each technology mbc = maximum built capacity
    
mbc = mbc.loc[mbc.variable_name == 'invest', ['value', 'oemof_tuple']]

print(mbc)
    # rename the index with the name of the investment flow 
# rename the index with the name of the investment flow 
a = 0
while a < mbc.index.size:
    mbc.rename(index= { mbc.index[a]: (mbc.loc[mbc.index[a],'oemof_tuple'])}, inplace= True)
    a+=1

fn = os.path.join(os.path.dirname(__file__), 'built_capacities_source_x.csv')
pd.DataFrame(mbc).to_csv(fn)


mbc.plot(kind = 'bar')

df = processing.create_dataframe(om)
# creating a result dictionary containing node parameters
p_results = processing.param_results(om)


fn = os.path.join(os.path.dirname(__file__), 'sum flow elec bus.xlsx')
electricity_bus['sequences'].sum(axis=0).to_excel(fn)
     
fn = os.path.join(os.path.dirname(__file__), 'sum_flow_pvbus.xlsx')
pv_bus['sequences'].sum(axis=0).to_excel(fn)

fn = os.path.join(os.path.dirname(__file__), 'sum flow wind off bus.xlsx')
wind_off_bus['sequences'].sum(axis=0).to_excel(fn) 

# plot the time series (sequences) of a specific component/bus
if plt is not None:

            plt.show()
            electricity_bus['sequences'].plot(kind='line', drawstyle='steps-post')
            plt.show()

fn = os.path.join(os.path.dirname(__file__), 'electricity bus_sequences.xlsx')
electricity_bus['sequences'].to_excel(fn)

if plt is not None:

            plt.show()
            wind_off_bus['sequences'].plot(kind='line', drawstyle='steps-post')
            plt.show()

fn = os.path.join(os.path.dirname(__file__), 'windoffshore bus sequences.xlsx')
wind_off_bus['sequences'].to_excel(fn)

if plt is not None:

            plt.show()
            pv_bus['sequences'].plot(kind='line', drawstyle='steps-post')
            plt.show()

fn = os.path.join(os.path.dirname(__file__), 'pv bus sequences.xlsx')
pv_bus['sequences'].to_excel(fn)

if plt is not None:

            plt.show()
            storage['sequences'].plot(kind='line', drawstyle='steps-post')
            plt.show()

fn = os.path.join(os.path.dirname(__file__), 'storage sequences.xlsx')
storage['sequences'].to_excel(fn)

# print the solver results
print('********* Meta results *********')
pp.pprint(es.energysystem.results['meta'])
print('')
    
# print the sums of the flows around the electricity bus
print('********* Main results electricity bus *********')
print(electricity_bus['sequences'].sum(axis=0))
          
# print the sums of the flows around the electricity bus
print('********* Main results wind off bus *********')
print(wind_off_bus['sequences'].sum(axis=0))

# print the sums of the flows around the electricity bus
print('********* Main results pv bus *********')
print(pv_bus['sequences'].sum(axis=0))      
