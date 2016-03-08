import boto3
import json
import datetime

ec2_client = boto3.client('ec2')
sns_client = boto3.client('sns')

dry_run = True
days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

now = datetime.datetime.utcnow()
current_day = days[now.weekday()]
current_hour = now.hour

def handler(event, context):

    # still need to handle regions

    print('current_day: %s' % current_day)
    print('current_hour: %s' % current_hour)
    print('dry_run: %s' % dry_run)

    # describe instance with tag name 'Schedule'
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

    # loop through described instances and store the id, state, and schedule value of those that have valid JSON data
    instances = []

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            for tag in instance['Tags']:
                if tag['Key'] == 'Schedule':
                    try:
                        schedule = json.loads(tag['Value'])
                    except Exception as e:
                        print('Schedule tag value is either missing or not formatted correctly: '
                              'Instance ID: %s, Value: %s' % (instance['InstanceId'], tag['Value']))
                        print(e)
                        continue

                    print('InstanceId: %s, State: %s' % (instance['InstanceId'], instance['State']['Name']))

                    instances.append({
                        'id': instance['InstanceId'],
                        'schedule': schedule,
                        'state': instance['State']['Name'],
                    })

    print('instances: %s' % instances)

    # loop through instances with a valid JSON in the schedule value and determine desired state
    for instance in instances[:]:

        if current_day in instance['schedule']:

            start_hour = instance['schedule'][current_day]['s'] if 's' in instance['schedule'][current_day] else None
            end_hour = instance['schedule'][current_day]['e'] if 'e' in instance['schedule'][current_day] else None

            print('start_hour: %s' % start_hour)
            print('end_hour: %s' % end_hour)

            if current_hour >= start_hour and current_hour >= end_hour:
                instance['desired_state'] = 'running' if start_hour > end_hour else 'stopped'
            elif current_hour >= start_hour:
                instance['desired_state'] = 'running'
            elif current_hour >= end_hour:
                instance['desired_state'] = 'stopped'
            else:
                instances.remove(instance)
        else:
            instances.remove(instance)

    print('instances: %s' % instances)

    # loop through instances and compare current state to desired state
    ids_to_start = []
    ids_to_stop = []

    for instance in instances:
        if instance['state'] != instance['desired_state'] and instance['state'] in ('running', 'stopped'):
            if instance['desired_state'] == 'stopped':
                ids_to_stop.append(instance['id'])
            elif instance['desired_state'] == 'running':
                ids_to_start.append(instance['id'])

    print('ids_to_start: %s' % ids_to_start)
    print('ids_to_stop: %s' % ids_to_stop)

    # start the appropriate instances
    if ids_to_start:
        try:
            response = ec2_client.start_instances(
                DryRun=dry_run,
                InstanceIds=ids_to_start
            )
        except:
            print("Running in DRY_RUN mode.")

        print('ids_to_start response HTTPStatusCode: %s' % response['ResponseMetadata']['HTTPStatusCode'])

    # stop the appropriate instances
    if ids_to_stop:
        try:
            response = ec2_client.stop_instances(
                DryRun=dry_run,
                InstanceIds=ids_to_stop
            )
        except:
            print("Running in DRY_RUN mode.")

        print('ids_to_stop response HTTPStatusCode: %s' % response['ResponseMetadata']['HTTPStatusCode'])

    return True
