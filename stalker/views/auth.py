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

from pyramid.httpexceptions import HTTPFound, HTTPOk, HTTPServerError
from pyramid.security import authenticated_userid, forget, remember
from pyramid.view import view_config, forbidden_view_config
from sqlalchemy import or_

import stalker
from stalker import User, Department, Group, Tag, Project, Entity, Studio
from stalker.db import DBSession
from stalker.views import log_param

import logging
from stalker import log
logger = logging.getLogger(__name__)
logger.setLevel(log.logging_level)


@view_config(
    route_name='dialog_create_user',
    renderer='templates/auth/dialog_create_user.jinja2'
)
def dialog_create_user(request):
    """called by create user dialog
    """
    login = authenticated_userid(request)
    logged_user = User.query.filter_by(login=login).first()

    department_id = request.matchdict['department_id']
    department = Department.query.filter_by(id=department_id).first()

    return {
        'mode': 'CREATE',
        'logged_user': logged_user,
        'department': department
    }


@view_config(
    route_name='dialog_update_user',
    renderer='templates/auth/dialog_create_user.jinja2'
)
def dialog_update_user(request):
    """called when updating a user
    """
    login = authenticated_userid(request)
    logged_user = User.query.filter_by(login=login).first()
    
    user_id = request.matchdict['user_id']
    user = User.query.filter_by(id=user_id).first()
    
    return {
        'mode': 'UPDATE',
        'logged_user': logged_user,
        'user': user
    }


@view_config(
    route_name='create_user'
)
def create_user(request):
    """called when adding a User
    """
    login = authenticated_userid(request)
    logged_user = User.query.filter_by(login=login).first()
    
    name = request.params.get('name', None)
    login = request.params.get('login', None)
    email = request.params.get('email', None)
    password = request.params.get('password', None)
    department_id = request.params.get('department_id', None)
    
    # create and add a new user
    if name and login and email and password:
        departments = []

        if department_id:
            department = Department.query.filter_by(id=department_id).first()
            departments = [department]
        else:
            # Departments
            if 'department_ids' in request.params:
                dep_ids = [
                    int(dep_id)
                    for dep_id in request.POST.getall('department_ids')
                ]
                departments = Department.query.filter(
                                Department.id.in_(dep_ids)).all()
    
    # Groups
        groups = []
        if 'group_ids' in request.params:
            grp_ids = [
                int(grp_id)
                for grp_id in request.POST.getall('group_ids')
            ]
            groups = Group.query.filter(
                            Group.id.in_(grp_ids)).all()
        
        # Tags
        tags = []
        if 'tag_ids' in request.params:
            tag_ids = [
                int(tag_id)
                for tag_id in request.POST.getall('tag_ids')
            ]
            tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
        
        logger.debug('creating new user')
        new_user = User(
            name=request.params['name'],
            login=request.params['login'],
            email=request.params['email'],
            password=request.params['password'],
            created_by=logged_user,
            departments=departments,
            groups=groups,
            tags=tags
        )
        
        logger.debug('adding new user to db')
        DBSession.add(new_user)
        logger.debug('added new user successfully')
    else:
        logger.debug('not all parameters are in request.params')
        log_param(request, 'name')
        log_param(request, 'login')
        log_param(request, 'email')
        log_param(request, 'password')
        HTTPServerError()
    
    return HTTPOk()


@view_config(
    route_name='update_user'
)
def update_user(request):
    """called when updating a User
    """
    login = authenticated_userid(request)
    logged_user = User.query.filter_by(login=login).first()
    
    user_id = int(request.matchdict['user_id'])
    name = request.params.get('name', None)
    login = request.params.get('login', None)
    email = request.params.get('email', None)
    password = request.params.get('password', None)
    
    # create and add a new user
    if name and login and email and password:
        departments = []

        # Departments
        if 'department_ids' in request.params:
            dep_ids = [
                int(dep_id)
                for dep_id in request.POST.getall('department_ids')
            ]
            departments = Department.query \
                .filter(Department.id.in_(dep_ids)).all()

        # Groups
        groups = []
        if 'group_ids' in request.params:
            grp_ids = [
                int(grp_id)
                for grp_id in request.POST.getall('group_ids')
            ]
            groups = Group.query \
                .filter(Group.id.in_(grp_ids)).all()
        
        # Tags
        tags = []
        if 'tag_ids' in request.params:
            tag_ids = [
                int(tag_id)
                for tag_id in request.POST.getall('tag_ids')
            ]
            tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
        
        logger.debug('creating new user')
        user = User.query.filter(User.id==user_id).first()
        
        user.name = name
        user.login = login
        user.email = email
        user.updated_by = logged_user
        user.departments = departments
        user.groups = groups
        user.tags = tags
        
        password = request.params['password']
        if password != 'DONTCHANGE':
            user.password = password
        
        logger.debug('updating user')
        DBSession.add(user)
        logger.debug('updated user successfully')
    else:
        logger.debug('not all parameters are in request.params')
        log_param(request, 'name')
        log_param(request, 'login')
        log_param(request, 'email')
        log_param(request, 'password')
        HTTPServerError()
    
    return HTTPOk()


@view_config(
    route_name='get_users',
    renderer='json',
    permission='Read_User'
)
def get_users(request):
    """returns all the users in database
    """
    return [
        {'id': user.id, 'name': user.name}
        for user in User.query.all()
    ]


@view_config(
    route_name='get_groups',
    renderer='json',
    permission='List_Group'
)
def get_groups(request):
    """returns all the groups in database
    """
    return [
        {'id': group.id, 'name': group.name}
        for group in Group.query.all()
    ]


@view_config(
    route_name='get_users_byEntity',
    renderer='json',
    permission='Read_User'
)
def get_users_byEntity(request):
    """returns all the Users of a given Entity
    """
    entity_id = request.matchdict['entity_id']
    entity = Entity.query.filter_by(id=entity_id).first()

    users = []

    for user in entity.users:
        departmentStr = ''
        groupStr = ''
        for department in user.departments:
            departmentStr += '<a class="DataLink" href="#" stalker_target="central_content" stalker_href="view/department/%s">%s</a><br/> ' % (department.id,department.name)
        for group in user.groups:
            groupStr += '<a class="DataLink" href="#" stalker_target="central_content" stalker_href="view/group/%s">%s</a><br/> ' % (group.id,group.name)
        users.append({
            'id': user.id,
            'name': user.name,
            'login': user.login,
            'email': user.email,
            'departments': departmentStr,
            'groups': groupStr,
            'tasksCount': len(user.tasks) ,
            'ticketsCount': len(user.open_tickets)
        })

    # works for Departments and Projects or any entity that has users attribute
    return users


@view_config(
    route_name='get_users_not_in_entity',
    renderer='json',
    permission='Read_User'
)
def get_users_not_in_entity(request):
    """returns all the Users which are not related with the given Entity
    """
    entity_id = request.matchdict['entity_id']
    entity = Entity.query.filter_by(id=entity_id).first()

    entity_class = None
    if entity.entity_type == 'Project':
        entity_class = Project
    elif entity.entity_type == 'Department':
        entity_class = Department

    logger.debug(User.query.filter(User.notin_(entity_class.users)).all())


    # works for Departments and Projects or any entity that has users attribute
    return [
        {
            'id': user.id,
            'name': user.name,
            'login': user.login,
            'tasksCount': '2',
            'ticketsCount': '2'
        }
        for user in entity.users
    ]


@view_config(
    route_name='dialog_append_users',
    renderer='templates/auth/dialog_append_users.jinja2'
)
def append_user_dialog(request):
    """runs for append user dialog
    """
    login = authenticated_userid(request)
    logged_user = User.query.filter_by(login=login).first()
    
    entity_id = request.matchdict['entity_id']
    entity = Entity.query.filter_by(id=entity_id).first()
    
    return {
        'user': logged_user,
        'entity': entity
    }

@view_config(
    route_name='append_user'
)
def append_user(request):
    """appends the given user to the given Project or Department
    """
    # user
    user_id = request.params.get('user_id', None)
    user = User.query.filter(User.id==user_id).first()
    
    # entity
    entity_id = request.params.get('entity_id', None)
    entity = Entity.query.filter(Entity.id==entity_id).first()
    
    if user and entity:
        entity.users.append(user)
        DBSession.add_all([entity, user])
    
    return HTTPOk()


@view_config(
    route_name='append_users'
)
def append_users(request):
    """appends the given users o the given Project or Department
    """
    # users
    user_ids = [
        int(u_id)
        for u_id in request.POST.getall('entity_users')
    ]
    users = User.query.filter(User.id.in_(user_ids)).all()
    
    # entity
    entity_id = request.params.get('entity_id', None)
    entity = Entity.query.filter(Entity.id==entity_id).first()
    
    logger.debug('entity : %s' % entity)
    logger.debug('users  : %s' % users)
    
    if users and entity:
        entity.users = users
        DBSession.add(entity)
        DBSession.add_all(users)
    
    return HTTPOk()


@view_config(
    route_name='create_group',
    renderer='templates/auth/create_groups.jinja2',
    permission='Create_Group'
)
def create_group(request):
    """runs when creating a new Group
    """
    return {}


@view_config(
    route_name='summarize_user',
    renderer='templates/auth/content_summarize_user.jinja2'
)
@view_config(
    route_name='view_user_tasks',
    renderer='templates/task/content_list_tasks.jinja2'
)
def summarize_user(request):
    """runs when getting general User info
    """
    # get the user id
    user_id = request.matchdict['user_id']
    user = User.query.filter_by(id=user_id).first()
    
    return {
        'user': user
    }


@view_config(
    route_name='view_user',
    renderer='templates/auth/page_view_user.jinja2'
)
def view_user(request):
    
    user_id = request.matchdict['user_id']
    user = User.query.filter_by(id=user_id).first()
    
    return {
        'user': user
    }

@view_config(
    route_name='list_users',
    renderer='templates/auth/content_list_users.jinja2'
)
def view_users(request):
    """
    """
    entity_id = request.matchdict['entity_id']
    entity = Entity.query.filter_by(id=entity_id).first()

    return {
        'entity': entity

    }


@view_config(route_name='logout')
def logout(request):
    headers = forget(request)
    return HTTPFound(
        location=request.route_url('login'),
        headers=headers
    )


@view_config(
    route_name='login',
    renderer='templates/auth/login.jinja2'
)
def login(request):
    """the login view
    """
    logger.debug('login start')
    login_url = request.route_url('login')
    referrer = request.url
    if referrer == login_url:
        referrer = '/'

    came_from = request.params.get('came_from', referrer)
    message = ''
    login = ''
    password = ''

    if 'form.submitted' in request.params:
        login = request.params['login']
        password = request.params['password']

        # need to find the user
        # check with the login or email attribute
        user_obj = User.query\
            .filter(or_(User.login==login, User.email==login)).first()

        if user_obj:
            login = user_obj.login

        if user_obj and user_obj.check_password(password):
            headers = remember(request, login)
            return HTTPFound(
                location=came_from,
                headers=headers,
            )

        message = 'Wrong username or password!!!'

    logger.debug('login end')
    return dict(
        message=message,
        url=request.application_url + '/login',
        came_from=came_from,
        login=login,
        password=password,
        stalker=stalker
    )


@forbidden_view_config(
    renderer='templates/auth/no_permission.jinja2'
)
def forbidden(request):
    """runs when user has no permission for the requested page
    """
    return {}


@view_config(route_name='home',
            renderer='templates/base.jinja2')
@view_config(route_name='me_menu',
             renderer='templates/auth/me_menu.jinja2')
def home(request):
    login = authenticated_userid(request)
    user = User.query.filter_by(login=login).first()
    studio = Studio.query.first()
    projects = Project.query.all()
    return {
        'stalker': stalker,
        'user': user,
        'projects': projects,
        'studio': studio,
    }


@view_config(
    route_name='check_login_availability',
    renderer='json'
)
def check_login_availability(request):
    """checks it the given login is available
    """
    login = request.matchdict['login']
    logger.debug('checking availability for: %s' % login)
    
    available = 1
    if login:
        user = User.query.filter(User.login==login).first()
        if user:
            available = 0
    
    return {
        'available': available
    }


@view_config(
    route_name='check_email_availability',
    renderer='json'
)
def check_email_availability(request):
    """checks it the given email is available
    """
    email = request.matchdict['email']
    logger.debug('checking availability for: %s' % email)
    
    available = 1
    if email:
        user = User.query.filter(User.email==email).first()
        if user:
            available = 0
    
    return {
        'available': available
    }
