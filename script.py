from zabbix_utils import ZabbixAPI

def get_hosts(hostnames):
    unmonitored = set(hostnames)
    monitored = set()
    exit = False
    while exit == False:
        print(f"You are monitoring {len(monitored)} of {len(hostnames)} hosts")
        state = input("Would you like to add a host to the monitoring list, remove a host from the monitoring list, or exit and save changes? [a/r/e] ")
        if state.lower() == "a":
            print(f"Unmonitored hosts: {unmonitored}")
            if len(unmonitored) == 0:
                print("No more hosts to monitor")
            else:
                print(f"There are {len(unmonitored)} left to monitor: {unmonitored}")
                hostname = None
                while hostname == None:
                    user_input = input("Please enter a host to monitor: ")
                    if user_input not in unmonitored:
                        print("Please enter a valid hostname that is not currently monitored")
                    else:
                        hostname = user_input
                unmonitored.remove(hostname)
                monitored.add(hostname)
        elif state.lower() == "r":
            print(f"Monitored hosts: {monitored}")
            if len(unmonitored) == 0:
                print("No currently monitored hosts")
            else:
                print(f"There are {len(monitored)} hosts to be monitored: {monitored}")
                hostname = None
                while hostname == None:
                    user_input = input("Please enter a host to remove from monitoring list: ")
                    if user_input not in unmonitored:
                        print("Please enter a valid hostname that is currently monitored")
                    else:
                        hostname = user_input
                monitored.remove(hostname)
                unmonitored.add(hostname)
        elif state.lower() == "e":
            exit = True
        else:
            print("Please tye either 'a', 'r', or 'e'")
    
    return monitored



def controller(input_url, input_user, input_password, service): # TODO: Add support for API token login
    api = ZabbixAPI(url=input_url)
    api.login(user="Admin", password="zabbix")
    session = api.user.login(username=input_user, password=input_password, userData=True)
    
    if session['type'] != 3:
        print("User does npot have required priviledges (Super admin)")
        api.logout()
        return 0
    
    systemdtemplate = None
    templates = api.template.get()
    for template in templates:
        if template['name'] == "Systemd by Zabbix agent 2":
            systemdtemplate = template
    if systemdtemplate == None: 
        print("Zabbix server does not have 'Systemd by Zabbix agent 2 installed. Please install and configure it before running this script.")
        api.logout()
        return 0
    
    hosts = api.host.get(templateids=[systemdtemplate['templateid']])
    hostnames = [h['host'] for h in hosts]
    print(f"Found {len(hosts)} hosts with Systemd template access: {hostnames}")
    if input("Is this expected? [Y/n] ") in "noNoNO" and not "":
        print("Ok, please give the desired hosts the 'Systemd by Zabbix agent 2' template via the web interface")
        api.logout()
        return 0
    
    hosts = list(get_hosts(hostnames))
    
    scipts = api.script.get(
        
    )
    api.script.create(
        name=f"restart {service}",
        command=f"sudo -u root /bin/systemctl restart {service}",
        type=0,
        scope=1,
        execute_on=0
    )
    
    api.action.create(
        esc_period="1m",
        name=f"Restart {service}",
        operations=[]
    )
    
    users = api.user.get(
        output=['userid','name']
    )

    for user in users:
        print(user['name'])
    
    api.logout()

if __name__ == "__main__":
    # url = input("URL: ")
    # user = input("USER: ")
    # password = input("PASSWORD: ")
    service = input("SERVICE: ")
    (url, user, password) = ("localhost:8080", "Admin", "zabbix")
    controller(url, user, password, service)