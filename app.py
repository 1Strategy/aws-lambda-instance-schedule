import boto3
import json
import datetime

ec2_client = boto3.client('ec2')

dry_run = True
days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

now = datetime.datetime.utcnow()
current_day = days[now.weekday()]
current_hour = now.hour


def handler(event, context):
    print('current_day: %s' % current_day)
    print('current_hour: %s' % current_hour)
    print('dry_run: %s' % dry_run)

    # describe instance with tag name 'Schedule'
    response = describe_instances()

    # loop through described instances and store the id, state, and schedule value of those that have valid JSON data
    instances_to_start = []
    instances_to_stop = []

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            for tag in instance['Tags']:
                if tag['Key'] == 'Schedule':
                    try:
                        schedule = json.loads(tag['Value'])

                    # exception if schedule value is not valid json
                    except Exception as e:
                        print('Schedule tag value is either missing or not formatted correctly: '
                              'Instance ID: %s, Value: %s' % (instance['InstanceId'], tag['Value']))
                        print(e)
                        continue

                    else:
                        # call determine_desired_state function and schedule
                        desired_state = determine_desired_state(schedule)
                        if instance['State']['Name'] != desired_state and instance['State']['Name'] in ('running', 'stopped'):
                            if desired_state == 'running':
                                instances_to_start.append(instance['InstanceId'])
                            elif desired_state == 'stopped':
                                instances_to_stop.append(instance['InstanceId'])

    # start/stop instances based on schedule determined above
    if instances_to_start:
        print(start_instances(instances_to_start))
    if instances_to_stop:
        print(stop_instances(instances_to_stop))

    return True


# describe instances that have 'Schedule' tag
def describe_instances():
    response = ec2_client.describe_instances(
        Filters=[
            {
                'Name': 'tag-key',
                'Values': [
                    'Schedule',
                ]
            },
        ]
    )

    return response


# determine desired state of instance with schedule argument
def determine_desired_state(schedule):
    if current_day in schedule:
        start_hour = schedule[current_day]['s'] if 's' in schedule[current_day] else None
        end_hour = schedule[current_day]['e'] if 'e' in schedule[current_day] else None

        if current_hour >= start_hour and current_hour >= end_hour:
            return 'running' if start_hour > end_hour else 'stopped'
        elif current_hour >= start_hour:
            return 'running'
        elif current_hour >= end_hour:
            return 'stopped'
        else:
            return None

    else:
        return None


# batch start instances
def start_instances(instances):
    try:
        response = ec2_client.start_instances(
            DryRun=dry_run,
            InstanceIds=instances
        )

    except Exception as e:
        print("No action taken - dry_run is true: %s" % e)
        return False

    else:
        return response


# batch stop instances
def stop_instances(instances):
    try:
        response = ec2_client.stop_instances(
            DryRun=dry_run,
            InstanceIds=instances
        )

    except Exception as e:
        print("No action taken - dry_run is true: %s" % e)
        return False

    else:
        return response
