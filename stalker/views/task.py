# -*- coding: utf-8 -*-
# Stalker a Production Asset Management System
# Copyright (C) 2009-2013 Erkan Ozgur Yilmaz
# 
# This file is part of Stalker.
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA


import datetime
import json
import logging

from pyramid.view import view_config
from pyramid.security import authenticated_userid
from pyramid.httpexceptions import HTTPServerError, HTTPOk
import transaction
from sqlalchemy.exc import IntegrityError

from stalker.db import DBSession
from stalker import (User, Task, Entity, Project, StatusList, Status,
                     TaskJugglerScheduler, Studio)
from stalker.models.task import CircularDependencyError
from stalker import defaults
from stalker import log
from stalker.views import get_datetime

logger = logging.getLogger(__name__)
logger.setLevel(log.logging_level)


def convert_to_jquery_gantt_task_format(tasks):
    """Converts the given tasks to the jQuery Gantt compatible json format.
    
    :param tasks: List of Stalker Tasks.
    :return: json compatible dictionary
    """
    
    data_source = Studio.query.first()
    logger.debug('data_source : %s' % data_source)
    
    if not data_source:
        data_source = defaults
    
    dwh = data_source.daily_working_hours
    wwh = data_source.weekly_working_hours
    wwd = data_source.weekly_working_days
    ywd = data_source.yearly_working_days
    timing_resolution = data_source.timing_resolution
    
    # it should work both for studio and defaults
    working_hours = {
        'mon': data_source.working_hours['mon'],
        'tue': data_source.working_hours['tue'],
        'wed': data_source.working_hours['wed'],
        'thu': data_source.working_hours['thu'],
        'fri': data_source.working_hours['fri'],
        'sat': data_source.working_hours['sat'],
        'sun': data_source.working_hours['sun']
    }
    logger.debug('studio.working_hours : %s' % working_hours)
    
    # create projects list to only list related projects
    projects = []
    for task in tasks:
        if task.project not in projects:
            projects.append(task.project)
    
    faux_tasks = []
    
    # first append projects
    
    faux_tasks.extend(
        [{
            'type': project.entity_type,
            'id': project.id,
            'code': project.code,
            'name': project.name,
            'start': int(project.start.strftime('%s')) * 1000,
            'end': int(project.end.strftime('%s')) * 1000,
            'schedule_model': 'duration',
            'schedule_timing': project.duration.days,
            'schedule_unit': 'd',
            'parent_id': None,
            'depend_id': [],
            'resources': [],
        } for project in projects]
    )
    
    faux_tasks.extend([
        {
            'type': task.entity_type,
            'id': task.id,
            'name': task.name,
            'code': task.id,
            'description': task.description,
            'status': 'STATUS_UNDEFINED',
            'project_id': task.project.id,
            'parent_id': task.parent.id if task.parent else task.project.id,
            'depend_ids': [dep.id for dep in task.depends],
            'resources': [
                {
                    'id': resource.id,
                } for resource in task.resources
            ],
            'start': int(task.start.strftime('%s')) * 1000,
            'end': int(task.end.strftime('%s')) * 1000,
            'is_scheduled': task.is_scheduled,
            'schedule_timing': task.schedule_timing,
            'schedule_unit': task.schedule_unit,
            'bid_timing': task.bid_timing,
            'bid_unit': task.bid_unit,
            'schedule_model': task.schedule_model,
            'schedule_constraint': task.schedule_constraint,
            'schedule_seconds': task.schedule_seconds,
            'total_logged_seconds': task.total_logged_seconds,
            'computed_start': int(task.computed_start.strftime('%s')) * 1000 if task.computed_start else None,
            'computed_end': int(task.computed_end.strftime('%s')) * 1000 if task.computed_end else None,
        }
        for task in tasks
    ])
    
    
    data = {
        'tasks' : faux_tasks,
        'resources' : [{
            'id': resource.id,
            'name': resource.name
        } for resource in User.query.all()],
        'timing_resolution': (timing_resolution.days * 86400 +
                              timing_resolution.seconds) * 1000,
        'working_hours': working_hours,
        'daily_working_hours': dwh,
        'weekly_working_hours': wwh,
        'weekly_working_days': wwd,
        'yearly_working_days': ywd
        
        # "canWrite": 0,
        # "canWriteOnParent": 0
    }
    
    #logger.debug(data)
    
    logger.debug('loading gantt data:\n%s' % 
                json.dumps(data,
                           sort_keys=False,
                           indent=4,
                           separators=(',', ': ')
                )
    )
    return data
    


def update_with_jquery_gantt_task_data(json_data):
    """updates the given tasks in database
    
    :param data: jQueryGantt produced json string
    """
    
    # logger.debug(json_data)
    data = json.loads(json_data)
    
    # logger.debug('updating tasks with gantt data:\n%s' % 
    #              json.dumps(data,
    #                         sort_keys=False,
    #                         indent=4,
    #                         separators=(',', ': ')
    #              )
    # )
    
    
    task_name_replace_strs = [
        ' (Task)', ' (Project)', ' (Asset)', ' (Sequence)', ' (Shot)'
    ]
    
    # Updated Tasks
    for task_data in data['tasks']:
        # logger.debug('*********************************************')
        task_id = task_data['id']
        task_name = task_data['name'] # just take the part without 
                                      # the parenthesis
        for rstr in task_name_replace_strs:
            if task_name.endswith(rstr):
                task_name = task_name[:-len(rstr)]
        
        task_start = task_data['start']
        task_end = task_data['end']
        task_resource_ids = [resource_data['id']
                             for resource_data in task_data['resources']]
        task_description = task_data.get('description', '')
        
        task_schedule_timing = float(task_data['schedule_timing'])
        
        # no need to update parent, it will only be possible by using
        # Stalker's own task edit UI
        # 
        #task_parent = task_data.get('parent_id', '')
        
        # --------
        # Updated:
        # --------
        # task depend_ids are now real Stalker task id, no need to convert it
        # to something else
        task_depend_ids = task_data.get('depend_ids', [])
        
        # get the task itself
        task = None
        if not isinstance(task_id, basestring): 
            # update task
            task = Task.query.filter(Task.id==task_id).first()
        # The following will not happen anymore, no tasks are created out of
        # Stalker
        #elif task_id.startswith('tmp_'):
        #    # create a new Task
        #    task = Task()
        
        # update it
        if task:
            # logger.debug('task %s' % task)
            task.name = task_name
            # logger.debug('task.start given (raw)  : %s' % task_start)
            # logger.debug('task.start given (calc) : %s' % datetime.datetime.fromtimestamp(task_start/1000))
            task.start = datetime.datetime.fromtimestamp(task_start/1000)
            # logger.debug('task.start after set    : %s' % task.start)
            #task.duration = datetime.timedelta(task_duration)
            task.end = datetime.datetime.fromtimestamp(task_end/1000)
            
            task.schedule_timing = task_schedule_timing
            
            resources = User.query.filter(User.id.in_(task_resource_ids)).all()
            task.resources = resources
            
            task.description = task_description
            
            task_depends = Task.query.filter(Task.id.in_(task_depend_ids)).all()
            
            # logger.debug('task.parent : %s' % task.parent)
            # logger.debug('task_depends: %s' % task_depends)
            
            task.depends = task_depends
            DBSession.add(task)
    
    # logger.debug('*********************************************')
    
    # Deleted tasks
    #deleted_tasks = Task.query.filter(Task.id.in_(data['deletedTaskIds'])).all()
    #for task in deleted_tasks:
    #    DBSession.delete(task)
    
    # transaction will handle the commit don't bother doing anything


@view_config(
    route_name='update_gantt_tasks'
)
def update_gantt_tasks(request):
    """updates the given tasks with the given JSON data
    """
    # get the data
    data = request.params['prj']
    if data:
        update_with_jquery_gantt_task_data(data)
    return HTTPOk()


@view_config(
    route_name='dialog_update_task',
    renderer='templates/task/dialog_create_task.jinja2'
)
def update_task_dialog(request):
    """runs when updating a task
    """
    task_id = request.matchdict['task_id']
    task = Task.query.filter(Task.id==task_id).first()
    
    return {
        'mode': 'UPDATE',
        'project': task.project,
        'task': task,
        'parent': task.parent,
        'schedule_models': defaults.task_schedule_models
    }

@view_config(
    route_name='update_task',
    permission='Update_Task'
)
def update_task(request):
    """Updates the given task with the data coming from the request
    
    :param request: 
    :return:
    """
    # *************************************************************************
    # collect data
    parent_id = request.params.get('parent_id', None)
    if parent_id:
        parent = Task.query.filter(Task.id==parent_id).first()
    else:
        parent = None
    name = str(request.params.get('name', None))
    description = request.params.get('description', '')
    is_milestone = int(request.params.get('is_milestone', None))
    status_id = int(request.params.get('status_id', None))
    status = Status.query.filter_by(id=status_id).first()
    schedule_model = request.params.get('schedule_model') # there should be one
    schedule_timing = float(request.params.get('schedule_timing'))
    schedule_unit = request.params.get('schedule_unit')
    start = get_datetime(request, 'start_date', 'start_time')
    end = get_datetime(request, 'end_date', 'end_time')
    update_bid = request.params.get('update_bid')
    
    depend_ids = [
        int(d_id)
        for d_id in request.POST.getall('depend_ids')
    ]
    depends = Task.query.filter(Task.id.in_(depend_ids)).all()
    
    resource_ids = [
        int(r_id)
        for r_id in request.POST.getall('resource_ids')
    ]
    resources = User.query.filter(User.id.in_(resource_ids)).all()
    
    logger.debug('parent_id       : %s' % parent_id)
    logger.debug('parent          : %s' % parent)
    logger.debug('depend_ids      : %s' % depend_ids)
    logger.debug('depends         : %s' % depends)
    logger.debug('resource_ids    : %s' % resource_ids)
    logger.debug('resources       : %s' % resources)
    logger.debug('name            : %s' % name)
    logger.debug('description     : %s' % description)
    logger.debug('is_milestone    : %s' % is_milestone)
    logger.debug('status_id       : %s' % status_id)
    logger.debug('status          : %s' % status)
    logger.debug('schedule_model  : %s' % schedule_model)
    logger.debug('schedule_timing : %s' % schedule_timing)
    logger.debug('schedule_unit   : %s' % schedule_unit)
    logger.debug('start           : %s' % start)
    logger.debug('end             : %s' % end)
    logger.debug('update_bid      : %s' % update_bid)
    
    # get task
    task_id = request.matchdict['task_id']
    task = Task.query.filter(Task.id==task_id).first()
    
    # update the task
    if not task:
        return HTTPOk(detail='Task not updated')
    
    task.name = name
    task.description = description
    task.parent = parent
    task.depends = depends
    task.start = start
    task.end = end
    task.is_milestone = is_milestone
    task.status = status
    task.schedule_model = schedule_model
    task.schedule_unit = schedule_unit
    task.schedule_timing = schedule_timing
    task.resources = resources
    task._reschedule(task.schedule_timing, task.schedule_unit)
    if update_bid:
        task.bid_timing = task.schedule_timing
        task.bid_unit = task.schedule_unit
    
    return HTTPOk(detail='Task updated successfully')

def depth_first_flatten(task, task_array=None):
    """Does a depth first flattening on the child tasks of the given task.
    :param task: start from this task
    :param task_array: previous flattened task array
    :return: list of flat tasks
    """
    
    if task_array is None:
        task_array = []
    
    if task:
        if task not in task_array:
            task_array.append(task)
        # take a tour in children
        for child_task in task.children:
            task_array.append(child_task)
            # recursive call
            task_array = depth_first_flatten(child_task, task_array)
    
    return task_array

@view_config(
    route_name='get_root_tasks',
    renderer='json',
)
def get_root_tasks(request):
    """returns all the root tasks in the database related to the given project
    """
    project_id = request.matchdict.get('project_id')
    project = Project.query.filter_by(id=project_id).first()
    
    tasks = []
    
    root_tasks = Task.query\
                .filter(Task._project==project)\
                .filter(Task.parent==None).all()
    
    # do a depth first search for child tasks
    for root_task in root_tasks:
        logger.debug('root_task: %s, parent: %s' % (root_task, root_task.parent))
        tasks.extend(depth_first_flatten(root_task))
    
    return convert_to_jquery_gantt_task_format(tasks) 

@view_config(
    route_name='get_gantt_tasks',
    renderer='json',
    permission='List_Task'
)
def get_gantt_tasks(request):
    """returns all the tasks in the database related to the given entity in
    jQueryGantt compatible json format
    """
    entity_id = request.matchdict.get('entity_id')
    entity = Entity.query.filter_by(id=entity_id).first()
    
    tasks = []
    if entity:
        if entity.entity_type == 'Project':
            project = entity
            # get the tasks who is a root task
            root_tasks = Task.query\
                .filter(Task._project==project)\
                .filter(Task.parent==None).all()
            
            # do a depth first search for child tasks
            for root_task in root_tasks:
                # logger.debug('root_task: %s, parent: %s' % (root_task, root_task.parent))
                tasks.extend(depth_first_flatten(root_task))
        elif entity.entity_type == 'User':
            user = entity
            
            # sort the tasks with the project.id
            if user is not None:
                tasks = sorted(user.tasks, key=lambda task: task.project.id)
                
                user_tasks_with_parents = []
                for task in tasks:
                    user_tasks_with_parents.append(task)
                    parent = task.parent
                    while parent:
                        # just add unique parents
                        #if parent not in user_tasks_with_parents:
                        user_tasks_with_parents.append(parent)
                        parent = parent.parent
                
                
                # logger.debug('user_task_with_parents: %s' % user_tasks_with_parents)
                # logger.debug('tasks                 : %s' % tasks)
                tasks = list(set(user_tasks_with_parents))
        else: # Asset, Shot, Sequence
            project = entity.project
            start_from_task = entity
            # find the root task
            while start_from_task.parent:
                start_from_task = start_from_task.parent
            root_task = start_from_task
            tasks.extend(depth_first_flatten(root_task))
    
    tasks.sort(key=lambda x: x.start)
    
    # if log.logging_level == logging.DEBUG:
    #     logger.debug('tasks count: %i' % len(tasks))
    #     for task in tasks:
    #         logger.debug('------------------------------')
    #         logger.debug('task name: %s' % task.name)
    #         logger.debug('start date: %s' % task.start)
    #         logger.debug('end date: %s' % task.end)
    
    return convert_to_jquery_gantt_task_format(tasks)


@view_config(
    route_name='get_project_tasks',
    renderer='json',
    permission='List_Task'
)
def get_project_tasks(request):
    """returns all the tasks in the database related to the given entity in
    flat json format
    """
    # get all the tasks related in the given project
    project_id = request.matchdict.get('project_id')
    project = Project.query.filter_by(id=project_id).first()
    
    return [
        {
            'id': task.id,
            'name': '%s (%s)' % (task.name,
                                       task.entity_type),
        } for task in Task.query.filter(Task._project==project).all()]


@view_config(
    route_name='list_tasks',
    renderer='templates/task/content_list_tasks.jinja2',
    permission='Read_Task'
)
def list_tasks(request):
    """runs when viewing tasks of a TaskableEntity
    """
    login = authenticated_userid(request)
    # logged_in_user = User.query.filter_by(login=login).first()
    
    entity_id = request.matchdict['entity_id']
    entity = Entity.query.filter(Entity.id==entity_id).first()
    
    return {
        'entity': entity
    }



@view_config(
    route_name='dialog_create_task',
    renderer='templates/task/dialog_create_task.jinja2',
    permission='Create_Task'
)
def create_task_dialog(request):
    """only project information is present
    """
    entity_id = request.matchdict['entity_id']
    entity = Entity.query.filter_by(id=entity_id).first()
    
    parent = None
    if entity.entity_type == 'Project':
        project = entity
    else:
        project = entity.project
        parent = entity
        
    
    # project = Project.query.filter_by(id=project_id).first()
    
    return {
        'mode': 'CREATE',
        'project': project,
        'parent': parent,
        'schedule_models': defaults.task_schedule_models
    }


@view_config(
    route_name='dialog_create_child_task',
    renderer='templates/task/dialog_create_task.jinja2',
    permission='Create_Task'
)
def create_child_task_dialog(request):
    """generates the info from the given parent task
    """
    parent_task_id = request.matchdict['task_id']
    parent_task = Task.query.filter_by(id=parent_task_id).first()
    
    project = parent_task.project if parent_task else None
    
    return {
        'mode': 'CREATE',
        'project': project,
        'parent': parent_task,
        'schedule_models': defaults.task_schedule_models
    }


@view_config(
    route_name='dialog_create_dependent_task',
    renderer='templates/task/dialog_create_task.jinja2',
    permission='Create_Task'
)
def create_dependent_task_dialog(request):
    """runs when adding a dependent task
    """
    # get the dependee task
    depends_to_task_id = request.matchdict['task_id']
    depends_to_task = Task.query.filter_by(id=depends_to_task_id).first()
    
    project = depends_to_task.project if depends_to_task else None
     
    return {
        'mode': 'CREATE',
        'project': project,
        'depends_to': depends_to_task,
        'schedule_models': defaults.task_schedule_models
    }


@view_config(
    route_name='create_task',
    permission='Create_Task'
)
def create_task(request):
    """runs when adding a new task
    """
    login = authenticated_userid(request)
    logged_in_user = User.query.filter_by(login=login).first()
    
    # ***********************************************************************
    # collect params
    project_id = request.params.get('project_id', None)
    parent_id = request.params.get('parent_id', None)
    name = request.params.get('name', None)
    description = request.params.get('description', '')
    is_milestone = request.params.get('is_milestone', None)
    status_id = request.params.get('status_id', None)
    if status_id:
        status_id = int(status_id)
    schedule_model = request.params.get('schedule_model') # there should be one
    schedule_timing = float(request.params.get('schedule_timing'))
    schedule_unit = request.params.get('schedule_unit')
    
    # get the resources
    resources = []
    resource_ids = []
    if 'resource_ids' in request.params:
        resource_ids = [
            int(r_id)
            for r_id in request.POST.getall('resource_ids')
        ]
        resources = User.query.filter(User.id.in_(resource_ids)).all()
    
    logger.debug('project_id      : %s' % project_id)
    logger.debug('parent_id       : %s' % parent_id)
    logger.debug('name            : %s' % name)
    logger.debug('description     : %s' % description)
    logger.debug('is_milestone    : %s' % is_milestone)
    logger.debug('status_id       : %s' % status_id)
    logger.debug('schedule_model  : %s' % schedule_model)
    logger.debug('schedule_timing : %s' % schedule_timing)
    logger.debug('schedule_unit   : %s' % schedule_unit)
    logger.debug('resource_ids    : %s' % resource_ids)
    logger.debug('resources       : %s' % resources)
    
    kwargs = {}
    
    if project_id and name and is_milestone and status_id:
        
        # get the project
        project = Project.query.filter_by(id=project_id).first()
        kwargs['project'] = project
        
        # get the parent if exists
        parent = None
        if parent_id:
            parent = Task.query.filter_by(id=parent_id).first()
        
        kwargs['parent'] = parent
        
        # get the status_list
        status_list = StatusList.query.filter_by(
            target_entity_type='Task'
        ).first()
        
        logger.debug('status_list: %s' % status_list)
        
        # there should be a status_list
        if status_list is None:
            return HTTPServerError(
                detail='No StatusList found'
            )
        
        status = Status.query.filter_by(id=status_id).first()
        logger.debug('status: %s' % status)
        
        
        # get the dates
        start = get_datetime(request, 'start_date', 'start_time')
        end = get_datetime(request, 'end_date', 'end_time')
        
        logger.debug('start : %s' % start)
        logger.debug('end : %s' % end)
        
        # get the dependencies
        depend_ids = [
            int(d_id)
            for d_id in request.POST.getall('depend_ids')
        ]
        depends = Task.query.filter(Task.id.in_(depend_ids)).all()
        logger.debug('depends: %s' % depends)
        
        kwargs['name'] = name
        kwargs['description'] = description
        kwargs['status_list'] = status_list
        kwargs['status'] = status
        kwargs['created_by'] = logged_in_user
        
        kwargs['start'] = start
        kwargs['end'] = end
        
        kwargs['schedule_model'] = schedule_model
        kwargs['schedule_timing'] = schedule_timing
        kwargs['schedule_unit'] = schedule_unit
        
        kwargs['resources'] = resources
        kwargs['depends'] = depends
        
        try:
            new_task = Task(**kwargs)
            logger.debug('new_task.name %s' % new_task.name)
            logger.debug('new_task.status: %s' % new_task.status)
            DBSession.add(new_task)
        except (AttributeError, TypeError, CircularDependencyError) as e:
            logger.debug(e.message)
            error = HTTPServerError()
            error.title = str(type(e))
            error.detail = e.message
            return error
        else:
            DBSession.add(new_task)
            try:
                transaction.commit()
            except IntegrityError as e:
                logger.debug(e.message)
                transaction.abort()
                return HTTPServerError(detail=e.message)
            else:
                logger.debug('flushing the DBSession, no problem here!')
                DBSession.flush()
                logger.debug('finished adding Task')
    else:
        logger.debug('there are missing parameters')
        def get_param(param):
            if param in request.params:
                logger.debug('%s: %s' % (param, request.params[param]))
            else:
                logger.debug('%s not in params' % param)
        get_param('project_id')
        get_param('name')
        get_param('description')
        get_param('is_milestone')
        get_param('resource_ids')
        get_param('status_id')
        
        param_list = ['project_id', 'name', 'description',
                      'is_milestone', 'resource_ids', 'status_id']
 
        params = [param for param in param_list if param not in request.params]
        
        error = HTTPServerError()
        error.explanation = 'There are missing parameters: %s' % params
        return error
    
    return HTTPOk(detail='Task created successfully')


@view_config(
    route_name='get_user_tasks',
    renderer='json'
)
def get_user_tasks(request):
    """returns the user tasks as jQueryGantt json
    """
    # get user id
    user_id = request.matchdict['user_id']
    user = User.query.filter_by(id=user_id).first()
    
    # get tasks
    tasks = []
    if user is not None:
        tasks = sorted(user.tasks, key=lambda x: x.project.id)
        # add also all the parents
        user_tasks_with_parents = []
        for task in tasks:
            user_tasks_with_parents.append(task)
            current_parent = task.parent
            while current_parent:
                user_tasks_with_parents.append(current_parent)
                current_parent = current_parent.parent
        
        logger.debug('user_task_with_parents: %s' % user_tasks_with_parents)
        logger.debug('tasks                 : %s' % tasks)
        tasks = user_tasks_with_parents
    
    return convert_to_jquery_gantt_task_format(tasks)

@view_config(
    route_name='auto_schedule_tasks',
)
def auto_schedule_tasks(request):
    """schedules all the tasks of active projects
    """
    # get the studio
    studio = Studio.query.first()
    
    if studio:
        tj_scheduler = TaskJugglerScheduler()
        studio.scheduler = tj_scheduler
        
        logger.debug('studio.name: %s' % studio.name)
        logger.debug('studio.working_hours[0]: %s' % studio.working_hours[0])
        logger.debug('studio.daily_working_hours: %s' % studio.daily_working_hours)
        logger.debug('studio.to_tjp: %s' % studio.to_tjp)
        
        try:
            studio.schedule()
        except RuntimeError:
            return HTTPServerError()
    
    return HTTPOk()

@view_config(
    route_name='view_task',
    renderer='templates/task/page_view_task.jinja2'
)
def view_task(request):
    """runs when viewing a task
    """

    login = authenticated_userid(request)
    logged_in_user = User.query.filter_by(login=login).first()

    task_id = request.matchdict['task_id']
    task = Task.query.filter_by(id=task_id).first()

    return {
        'user': logged_in_user,
        'task': task
    }

@view_config(
    route_name='summarize_task',
    renderer='templates/task/content_summarize_task.jinja2'
)
def summarize_task(request):
    """runs when viewing an task
    """

    login = authenticated_userid(request)
    logged_in_user = User.query.filter_by(login=login).first()

    task_id = request.matchdict['task_id']
    task = Task.query.filter_by(id=task_id).first()

    return {
        'user': logged_in_user,
        'task': task
    }


