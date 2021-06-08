#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 11 10:49:45 2021

@author: yases
"""
import pandas as pd
import sqlalchemy
import psycopg2
import datetime
import pymysql

from bokeh.models.widgets import Panel, Tabs
from bokeh.models import ColumnDataSource, DataTable, TableColumn, Div, HTMLTemplateFormatter, DateRangeSlider, DateFormatter, CheckboxGroup, HoverTool, DaysTicker, RadioGroup, CustomJSHover, CategoricalColorMapper, NumberFormatter, NumeralTickFormatter
from bokeh.layouts import column, gridplot, layout, grid, row
from bokeh.io import show, curdoc
from bokeh.plotting import figure
from bokeh.palettes import Category10_10



#engine = sqlalchemy.create_engine('postgresql+psycopg2://admin:admin@localhost:5432/capstone')
#engine = sqlalchemy.create_engine('postgresql+psycopg2://admin:admin@host.docker.internal:5432/capstone')
engine = sqlalchemy.create_engine('mysql+pymysql://root:Kukku123MYSQL@host.docker.internal/vinpac')



# df = pd.read_sql_table('MachDetFillerStoppageEachDay', con=engine)
# df = df.loc[~df.Status.isin(['Running','Off'])]

linedf = pd.read_sql_table('machstoppageforfilleralldays', con=engine)


linedf = linedf.loc[~linedf.Status.isin(['Running','Off'])]

linedf['duration_sec'] = round(linedf['duration_sec'],3)





factors_str = ["Safety Stopped", "Starved",  "Blocked", "Faulted", "Unallocated", "User Stopped","Off", "Setup","Running", "Runout" ]
color_dict = {}
for x in Category10_10:
    cd = {factors_str[Category10_10.index(x)]:x}
    color_dict.update(cd)
del  x, cd
color_map = CategoricalColorMapper(factors=factors_str, palette=Category10_10)

def plotoverallformachines(df):
    m=df.groupby(['Filler_Status','Machine','Status']).sum().reset_index()
    m['duration_sec'] = round(m['duration_sec'],3)
    #m['duration_hr'] = pd.to_datetime(m["duration_sec"], unit='s').dt.strftime("%H:%M:%S")
    # duration_text = []
    # for value in m['duration_sec']:
    #     duration_text.append(secondsToText(value))
    # m['duration_text']= duration_text

    
    def const_d_table(data, machine):
        max_value_index = data.index[data['duration_sec']==data['duration_sec'].max()]
        sts = data['Status'][max_value_index]
        source = ColumnDataSource(data)
        template="""                
                <div style="color:<%= 
                    (function colorfromint(){
                        if (Status=="""+"'"+sts.iloc[0]+"'"+""")
                            {return('red')}
                        }()) %>;"> 
                    <%= value %>
                </div>
                """
        formatter =  HTMLTemplateFormatter(template=template)
        fmt = NumberFormatter(format="00:00:00")
       # cmpfmt = CompositeFormatter(formatters=[formatter,fmt])
        
        columns = [TableColumn(field="Status", title="Status",  formatter=formatter), TableColumn(field="Count", title="Freq",  formatter=formatter), TableColumn(field="duration_sec", title="Duration(s)",  formatter=formatter), TableColumn(field="duration_sec", title="Duration",  formatter=fmt)] 
        data_table = DataTable(source=source, columns=columns, width = 500,height=210, autosize_mode = 'fit_viewport')
        div = Div(text="""<b>"""+machine+""" Details</b>""")
        return (column(div, data_table))

    machines = df.Machine.unique()
    table_list = []
    for machine in machines:
        ndf = m.loc[m.Machine == machine]
        table_list.append(const_d_table(ndf,machine))
        
    grid = gridplot(table_list, ncols=3)
    div = Div(text="""<b> Overall Details</b>""",style={'font-size': '200%', 'color': 'blue'})
    g = column(div, grid, sizing_mode='stretch_width')
    
    return Panel(child = g, title="Overall Details")

#################################################################################################

def plotsubtabmachines(linedata, machine):
    
    mx_dt = max(linedata.Start_Time.dt.date)
    mi_dt= min(linedata.Start_Time.dt.date)
    fil_stat = linedata.Filler_Status.iat[0]
    #data = data.loc[data.Machine==machine]
    linedata = linedata.loc[linedata.Machine==machine]
    
    ## updating the data source for display
    
    def updatesrc(attr, old, new):
        
        status_to_use = [status_selection.labels[i] for i in status_selection.active]
        new_start= datetime.datetime.utcfromtimestamp(date_range.value[0]/1000)
        new_end = datetime.datetime.utcfromtimestamp(date_range.value[1]/1000)
        
        new_src, new_line_src, new_avg_source = makedataset(new_start, new_end, status_to_use)
        source.data.update(new_src.data)
        line_source.data.update(new_line_src.data)
        avg_source.data.update(new_avg_source.data)
        
    
    ## preparing the data source
    def makeavgdata(data):
        data_g = data.groupby('Status').agg({'Count':['sum','mean'], 'duration_sec':'sum'}).reset_index()
        data_g= data.groupby('Status').agg(Total_Count=('Count', 'sum'), Avg_Count=('Count', 'mean'), total_duration=('duration_sec','sum')).reset_index()
        data_g['avg_duration'] = round(data_g['total_duration']/data_g['Total_Count'],3)
        data_g['avg_duration'] = round(data_g['avg_duration'],3)
        data_g['total_duration'] = round(data_g['total_duration'],3)
        data_g['Avg_Count'] = round(data_g['Avg_Count'],3)
        return ColumnDataSource(data_g)
    
    def makelinedata(data):
        xs = []
        ys = []
        labels = []
        colors = []
        #duration_text = []
        status_to_use = data.Status.unique()
        for status in status_to_use:
            subset = data.loc[data['Status'] == status]
            xs.append(list(subset['Start_Time']))
            ys.append(list(subset['duration_sec']))
            #duration_text.append(list(subset['duration_text']))
            colors.append(color_dict.get(status))
            labels.append(status)
        new_src_line = ColumnDataSource(data = {'x':xs, 'y': ys, 'color':colors, 'label':labels})#, 'duration_text':duration_text})
        return new_src_line
    
    def makedataset(new_start, new_end, status_to_use ):
        
        data1 = linedata.loc[(linedata.Start_Time.dt.date >= pd.to_datetime(new_start)) & (linedata.Start_Time.dt.date <= pd.to_datetime(new_end))]
        data1 = data1.loc[data1.Status.isin(status_to_use)]
        
        source = ColumnDataSource(data1)
        line_source = makelinedata(data1)
        avg_source = makeavgdata(data1)
        return source, line_source , avg_source           
    ###----------------------------------------###
    
    def make_lineplot(src):
        title= machine +" status causing filler to go to " + fil_stat+ " state"
        p = figure(plot_width = 800, plot_height = 400, title = title, x_axis_label = 'Date', y_axis_label = 'Duration', x_axis_type="datetime")
        
        p.multi_line('x', 'y', color = 'color', legend = 'label',line_width = 1.5, source = src)
        # Hover tool with next line policy
        
        # pltsct = p.scatter('Start_Time', 'duration_sec',source=lblsrc, color={'field': 'Status', 'transform': color_map}, size= 1 )
        
        # hover = HoverTool(renderers=[pltsct],tooltips=[('Status', '@Status'), ('Date', '@Start_Time{%F}'), ('Duration', '@duration_text'),('Duration(s)', '@duration_sec{1.111}')], line_policy = 'next')
        
        # hover.formatters = { "@Start_Time": "datetime"} #, "duration_text": CustomJSHover(code = "return special_vars.duration_text + '_text'")}
        # # Add the hover tool and styling
        # p.add_tools(hover)
        
        hover = HoverTool(tooltips=[('Status', '@label'), ('Date', '$x{%F}'), ('Duration', '$y{‘00:00:00’}'),('Duration(s)', '$y{1.111}')], line_policy = 'next')
        
        hover.formatters = { "$x": "datetime", "$y": "numeral"}
        # Add the hover tool and styling
        p.add_tools(hover)

        p.xaxis.major_label_orientation = 3.4142/4
        
        p.xaxis.ticker = DaysTicker(days=list(range(min(linedf.Start_Time.dt.day),max(linedf.Start_Time.dt.day)+1)))
        p.yaxis.formatter=NumeralTickFormatter(format="00:00:00")
        
        p.xgrid.visible = False
        return p
    
    def make_table(source):
        datefmt = DateFormatter(format="%a, %d %b %Y")
        fmt = NumberFormatter(format="00:00:00")
        columns = [TableColumn(field="Start_Time", title="Date", formatter = datefmt),TableColumn(field="Status", title="Status"), TableColumn(field="Count", title="Freq"), TableColumn(field="duration_sec", title="Duration(s)"), TableColumn(field="duration_sec", title="Duration", formatter=fmt)] 
        data_table = DataTable(source=source, columns=columns, width=400, height=200, autosize_mode = 'fit_viewport')
        return data_table
    
    def make_average_table(source):
        fmt = NumberFormatter(format="00:00:00")
        columns = [TableColumn(field="Status",title="Status"), TableColumn(field="Total_Count", title="Total Stoppages"),TableColumn(field="total_duration", title="Total Duration", formatter=fmt), TableColumn(field="avg_duration", title="Average Duration", formatter=fmt)]
        data_table = DataTable(source=source, columns=columns, width=400, height=200, autosize_mode = 'fit_viewport')
        return data_table
    
    def make_avg_barplot(source):
        p = figure(x_range=source.data['Status'], plot_height=250, title="Average Stoppage Duration of each State", x_axis_label = 'Status', y_axis_label = 'Duration')
        p.vbar(x='Status', top='avg_duration', width=0.9, source=source, color={'field': 'Status', 'transform': color_map})
        p.y_range.start = 0
        p.yaxis.formatter=NumeralTickFormatter(format="00:00:00")
        p.xaxis.major_label_orientation = 3.4142/8

        return p
    
###############################Initial set up#############
    # Filters
    date_range = DateRangeSlider(value=(mi_dt, mx_dt),start=mi_dt, end=mx_dt, step=1*24*60*60*1000)
    date_range.on_change("value", updatesrc)
    
    statuses = linedata.Status.unique()
    available_status = list(set(statuses))
    status_selection = CheckboxGroup(labels=available_status, active =  list(range(len(available_status))), inline=True)
    status_selection.on_change('active', updatesrc)
    
    #initial sources
    source, line_source, avg_source = makedataset(mi_dt, mx_dt, available_status)
    
    #plots
    line_plot = make_lineplot(line_source)
    data_table = make_table(source)
    tab1_h = Div(text= """<b>Daily Status Details</b>""")
    col_t1 = column(tab1_h, data_table)
    avg_table = make_average_table(avg_source)
    tab2_h = Div(text= """<b>Combined Status Details</b>""")
    col_t2 = column(tab2_h, avg_table)
    bar_plot = make_avg_barplot(avg_source)
    
    filt_txt = Div(text="""<b>Filter</b>""")
    
    date_rang_h = Div(text="""<b>Choose Date Range<b>""")
    date_col = column(date_rang_h, date_range)
    
    status_h = Div(text="""<b>Choose Status</b>""")
    status_col = column(status_h, status_selection)
    
    c = row(date_col, status_col)

    fil_col = column(filt_txt, c)
    
    
    b = layout([[fil_col],[line_plot],[col_t1, bar_plot, col_t2]], sizing_mode = 'stretch_width')
    return b

    ######################################


#####################################################
# getting tabs for each machine in a filler stopped state
def getsubtabs(df):
    tabs_list = []
    tabs_list.append(plotoverallformachines(df))
    machines = df.Machine.unique()
    for machine in machines:
        #def makelineplotdataset(new_Start, new_end)
        b = plotsubtabmachines(df, machine)
        tabs_list.append(Panel(child = b, title=machine))
    
    tabs = Tabs(tabs=tabs_list)
    return tabs


# getting the tabs for each filler stopped state
filler_status = linedf.Filler_Status.unique()

main_tabs_list = []

for fstatus in filler_status:
    ndf = linedf.loc[linedf.Filler_Status==fstatus]
    mt = getsubtabs(ndf)
    main_tabs_list.append(Panel(child = mt, title=fstatus))
    
tabs = Tabs(tabs=main_tabs_list)

show(tabs)

curdoc().add_root(tabs)

