# ProjectDashboard

# running the dashboard
Download the file and rename it if running it for another container. 

bokeh serve <file_name>.py --port <new_port_for_bashboard> --allow-websocket-origin <tool_server_ip>:<tool_port_number>

Eg: bokeh serve dashboard.py --port 5006 --allow-websocket-origin 127.0.0.1:5000

To run the dashboard for new container, make appropriate connections to the database in line 21 : engine = sqlalchemy.create_engine('postgresql+psycopg2://admin:admin@localhost:5432/<new_schema_or_db_name>')


 
