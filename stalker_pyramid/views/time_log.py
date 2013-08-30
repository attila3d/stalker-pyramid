# -*- coding: utf-8 -*-
# Stalker Pyramid a Web Base Production Asset Management System
# Copyright (C) 2009-2013 Erkan Ozgur Yilmaz
# 
# This file is part of Stalker Pyramid.
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


import logging

from pyramid.httpexceptions import HTTPOk, HTTPServerError
from pyramid.view import view_config

from stalker import defaults, Task, User, Studio, TimeLog, Entity

from stalker.db import DBSession
from stalker.exceptions import OverBookedError
from stalker_pyramid.views import (get_logged_in_user,
                                   PermissionChecker, milliseconds_since_epoch,
                                   get_date)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@view_config(
    route_name='dialog_create_time_log',
    renderer='templates/time_log/dialog_create_time_log.jinja2',
)
def create_time_log_dialog(request):
    """creates a create_time_log_dialog by using the given task
    """
    logger.debug('inside create_time_log_dialog')

    # get logged in user
    logged_in_user = get_logged_in_user(request)
    if not logged_in_user:
        import auth
        return auth.logout(request)

    task_id = request.matchdict.get('id', -1)
    task = Task.query.filter(Task.task_id == task_id).first()

    studio = Studio.query.first()
    if not studio:
        studio = defaults

    return {
        'mode': 'CREATE',
        'has_permission': PermissionChecker(request),
        'studio': studio,
        'logged_in_user': logged_in_user,
        'task': task,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='dialog_update_time_log',
    renderer='templates/time_log/dialog_create_time_log.jinja2',
)
def update_time_log_dialog(request):
    """updates a create_time_log_dialog by using the given task
    """
    logger.debug('inside updates_time_log_dialog')

    # get logged in user
    logged_in_user = get_logged_in_user(request)
    if not logged_in_user:
        import auth
        return auth.logout(request)

    time_log_id = request.matchdict.get('id', -1)
    time_log = TimeLog.query.filter_by(id=time_log_id).first()

    studio = Studio.query.first()
    if not studio:
        studio = defaults

    return {
        'mode': 'UPDATE',
        'has_permission': PermissionChecker(request),
        'studio': studio,
        'logged_in_user': logged_in_user,
        'task': time_log.task,
        'time_log': time_log,
        'milliseconds_since_epoch': milliseconds_since_epoch
    }


@view_config(
    route_name='create_time_log'
)
def create_time_log(request):
    """runs when creating a time_log
    """

    logger.debug('inside create_time_log')
    task_id = request.params.get('task_id')
    task = Task.query.filter(Task.id == task_id).first()

    #**************************************************************************
    # collect data
    resource_id = request.params.get('resource_id', None)
    resource = User.query.filter(User.id == resource_id).first()

    start_date = get_date(request, 'start')
    end_date = get_date(request, 'end')

    logger.debug('task_id     : %s' % task_id)
    logger.debug('task        : %s' % task)
    logger.debug('resource_id : %s' % resource_id)
    logger.debug('start_date  : %s' % start_date)
    logger.debug('end_date    : %s' % end_date)

    if task and resource and start_date and end_date:
        # we are ready to create the time log
        # TimeLog should handle the extension of the effort
        logger.debug('got all the data')
        try:
            time_log = TimeLog(
                task=task,
                resource=resource,
                start=start_date,
                end=end_date
            )
        except OverBookedError:
            logger.debug('TimeLog thrown OverBookedError!')
            return HTTPServerError()
        else:
            DBSession.add(time_log)
        logger.debug('no problem here!')

    logger.debug('successfully created time log!')

    return HTTPOk()


@view_config(
    route_name='update_time_log'
)
def update_time_log(request):
    """runs when updating a time_log
    """
    logger.debug('inside update_time_log')
    time_log_id = int(request.params.get('time_log_id'))
    time_log = TimeLog.query.filter_by(id=time_log_id).first()

    #**************************************************************************
    # collect data
    resource_id = int(request.params.get('resource_id', None))
    resource = User.query.filter(User.id == resource_id).first()

    start_date = get_date(request, 'start')
    end_date = get_date(request, 'end')

    logger.debug('time_log_id : %s' % time_log_id)
    logger.debug('resource_id : %s' % resource_id)
    logger.debug('start_date  : %s' % start_date)
    logger.debug('end_date    : %s' % end_date)

    if time_log and resource and start_date and end_date:
        # we are ready to create the time log
        # TimeLog should handle the extension of the effort

        try:
            time_log.resource = resource
            time_log.start = start_date
            time_log.end = end_date
        except OverBookedError:
            return HTTPServerError()
        else:
            DBSession.add(time_log)

    return HTTPOk()


@view_config(
    route_name='get_entity_time_logs',
    renderer='json'
)
@view_config(
    route_name='get_task_time_logs',
    renderer='json'
)
def get_time_logs(request):
    """returns all the Shots of the given Project
    """
    logger.debug('get_time_logs is running')
    entity_id = request.matchdict.get('id', -1)
    entity = Entity.query.filter_by(id=entity_id).first()

    logger.debug('entity_id : %s' % entity_id)

    time_log_data = []

    # if entity.time_logs:
    for time_log in entity.time_logs:
        # logger.debug('time_log.task.id : %s' % time_log.task.id)
        # assert isinstance(time_log, TimeLog)
        time_log_data.append({
            'id': time_log.id,
            'task_id': time_log.task.id,
            'task_name': time_log.task.name,
            'parent_name': ' | '.join(
                [parent.name for parent in time_log.task.parents]),
            'resource_id': time_log.resource_id,
            'resource_name': time_log.resource.name,
            'duration': time_log.total_seconds,
            'start_date': milliseconds_since_epoch(time_log.start),
            'end_date': milliseconds_since_epoch(time_log.end)

            # 'hours_to_complete': time_log.hours_to_complete,
            # 'notes': time_log.notes
        })

    return time_log_data

