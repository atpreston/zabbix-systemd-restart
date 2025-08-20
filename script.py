from zabbix_utils import ZabbixAPI

def get_hosts(hostnames):
    if len(hostnames) == 0:
        print("No hosts available to monitor")
        return []
    unmonitored = set(hostnames)
    monitored = set()
    exit = False
    while exit == False:
        print(f"You are monitoring {len(monitored)} of {len(hostnames)} hosts")
        state = input("Would you like to (a)dd a host to the monitoring list, (r)emove a host from the monitoring list, or (e)xit and save changes? [a/r/e] ")
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
            if len(monitored) == 0:
                print("Please choose at least 1 host to monitor")
            else:
                exit = True
        else:
            print("Please type either 'a', 'r', or 'e'")
    
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
    expected = input("Is this expected? [Y/n] ")
    if expected.lower() == "no" or expected.lower() == "n":
        print("Ok, please give the desired hosts the 'Systemd by Zabbix agent 2' template via the web interface")
        api.logout()
        return 0
    
    hosts = list(get_hosts(hostnames))
    if len(hosts) == 0:
        return 0
    
    # TODO: add check that script has not already been created
    script = api.script.create(
        name=f"restart {service}",
        command=f"sudo -u root /bin/systemctl restart {service}",
        type=0,
        scope=1,
        execute_on=0
    )
    
    api.action.create(
        name=f"Restart {service} action",
        operations=[{
            'operationtype': 1,
            'opcommand': [script], # TODO: FIX THIS OBJECT PASSING TO API
            'opcommand_grp': "All",
        }],
        eventsource=1,
    )
    
    print("Please now add the following line to your sudoers config:")
    print(f"'zabbix ALL=(root)NOPASSWD: /bin/systemctl start {service}'")
    
    api.logout()

if __name__ == "__main__":
    # url = input("URL: ")
    # user = input("USER: ")
    # password = input("PASSWORD: ")
    service = input("SERVICE: ")
    (url, user, password) = ("localhost:8080", "Admin", "zabbix")
    controller(url, user, password, service)