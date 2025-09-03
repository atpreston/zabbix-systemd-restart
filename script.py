from zabbix_utils import ZabbixAPI

def login(url):
    # Note that token usage is not required for this case. The user account in the api.user login step must have Super Admin priviledge access, and so can be used in the first step.
    # If a token was used, a Super Admin username and password must be provided for the second step anyway.
    
    api = ZabbixAPI(url=url)
    username = input("Please enter a username: ")
    password = input(f"Please enter the password for {username}: ")
    
    api.login(user=username, password=password)
    session = api.user.login(username=username, password=password, userData=True)
    return (api, session)

def get_hosts(hostnames):
    if len(hostnames) == 0:
        print("No hosts available to monitor")
        return []
    monitored = set(hostnames)
    unmonitored = set()
    exited = False
    while exited == False:
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
                exited = True
        else:
            print("Please type either 'a', 'r', or 'e'")
    
    return monitored

def create_script(api, service):
    scripts = api.script.get()
    
    for s in scripts:
        if s['name'] == f"Restart {service} script":
            response = input(f"There is already a script called 'Restart {service} script'. Would you like to replace it? [Y/n] ")
            if response.lower() == "no" or response.lower() == "n":
                print("Duplicate scripts cannot be created. Exiting.")
                return 0
            else:
                api.script.delete(s['scriptid'])
    
    return api.script.create(
        name=f"Restart {service} script",
        command=f"sudo -u root /bin/systemctl restart {service}",
        type=0,
        scope=1,
        execute_on=0
    )

def get_triggers(api, service, hosts):
    triggers = api.trigger.get()
    triggers = [t for t in triggers if f"{service}" in t['description']]
    return triggers

def create_action(api, service, hosts):
    triggers = get_triggers(api, service, hosts)
    
    actions = api.action.get()
    for a in actions:
        if a['name'] == f"Restart {service} action":
            response = input(f"There is already an action called 'Restart {service} action'. Would you like to delete it? [Y/n] ")
            if response.lower() == "no" or response.lower() == "n":
                print("Duplicate actions cannot be created. Exiting.")
                return 0
            else:
                api.action.delete(a['actionid'])
    script = create_script(api, service)
    api.action.create(
        name=f"Restart {service} action",
        filter={
          'conditions': [
              {
                  'conditiontype': 2,
                  'operator': 0,
                  'value': triggers[0]['triggerid']
              }
          ],
          'evaltype': 0,
        },
        operations=[{
            'operationtype': 1,
            'opcommand': {
                'scriptid': int(script['scriptids'][0])
            },
            'opcommand_hst': [{'hostid': h['hostid']} for h in hosts],
        }],
        eventsource=0,
    )

def controller(api, session, service):
    if session['type'] != 3:
        print("User does not have required priviledges (Super admin)")
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
    
    chosenhosts = list(get_hosts(hostnames))
    if len(chosenhosts) == 0:
        return 0
    hosts = [h for h in hosts if h['host'] in chosenhosts] # filter to 'hosts' just has the selected hosts

    create_action(api, service, hosts)
    
    print("Please now add the following line to your sudoers config:")
    print(f"'zabbix ALL=(root)NOPASSWD: /bin/systemctl restart {service}'")
    
    api.logout()

if __name__ == "__main__":
    url = input("Please enter the URL of your Zabbix server: ")
    (api, session) = login(url)
    service = input("Please enter the name of the Systemd service you wish to restart (without any qualifications, i.e. 'bluetooth' not 'bluetooth.service'): ")
    controller(api, session, service)
