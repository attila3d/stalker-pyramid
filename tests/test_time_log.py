# -*- coding: utf-8 -*-
#
# Stalker Pyramid Copyright (C) 2013 Erkan Ozgur Yilmaz
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

import mocker

import unittest2
import transaction

from pyramid import testing
from stalker import (db, User, Status, StatusList, Repository, Project, Task,\
                    Group)
from stalker.db import DBSession
from stalker_pyramid.views import time_log


class TimeLogViewTestCase(unittest2.TestCase):
    """tests the time log view
    """

    def setUp(self):
        """setup the test
        """
        self.config = testing.setUp()
        db.setup({'sqlalchemy.url': 'sqlite:///:memory:'})
        db.init()

        DBSession.remove()
        # test users
        self.user1 = User(
            name='Test User 1',
            login='tuser1',
            email='tuser1@test.com',
            password='secret'
        )
        DBSession.add(self.user1)

        # create a couple of tasks
        self.status_new = Status(name='New', code='NEW')
        self.status_rts = Status(name='Ready To Start', code='RTS')
        self.status_wip = Status(name='Work In Progress', code='WIP')
        self.status_prev = Status(name='Pending Review', code='PREV')
        self.status_hrev = Status(name='Has Revisions', code='HREV')
        self.status_cmpl = Status(name='Complete', code='CMPL')

        self.project_status_list = StatusList(
            name='Project Statuses',
            target_entity_type='Project',
            statuses=[self.status_new, self.status_wip, self.status_cmpl]
        )
        DBSession.add(self.project_status_list)

        self.task_status_list = StatusList(
            name='Task Statuses',
            target_entity_type='Task',
            statuses=[self.status_new, self.status_rts, self.status_wip,
                      self.status_prev, self.status_hrev, self.status_cmpl]
        )
        DBSession.add(self.task_status_list)

        # repo
        self.repo = Repository(
            name='Test Repository'
        )
        DBSession.add(self.repo)

        # proj1
        self.proj1 = Project(
            name='Test Project',
            code='TProj1',
            status_list=self.project_status_list,
            repository=self.repo,
            lead=self.user1
        )
        DBSession.add(self.proj1)

        # tasks
        self.task1 = Task(
            name='Test Task 1',
            project=self.proj1,
            status_list=self.task_status_list,
            status=self.status_new,
            resources=[self.user1],
            schedule_timing=5,
            schedule_unit='d',
            schedule_model='effort'
        )
        DBSession.add(self.task1)
        transaction.commit()

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    def test_creating_a_time_log_for_a_task_with_status_new(self):
        """testing if an error response will be returned when trying to create
        time log for a task with status "new"
        """
        request = testing.DummyRequest()
        self.task1 = Task.query.filter(Task.name == self.task1.name).first()
        request.params['task_id'] = self.task1.id
        request.params['resource_id'] = self.task1.resources[0].id
        request.params['start'] = "Fri, 01 Nov 2013 08:00:00 GMT"
        request.params['end'] = "Fri, 01 Nov 2013 17:00:00 GMT"

        self.assertEqual(self.task1.status, self.status_new)
        response = time_log.create_time_log(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(
            response.body,
            'It is only possible to create time log for a task '
            'with status "RTS", "WIP", "PREV" or "HREV"'
        )
        self.assertEqual(self.task1.status, self.status_new)

    def test_creating_a_time_log_for_a_task_with_status_rts(self):
        """testing if the status of the time log will be set to WIP if the
        status of that task is rts
        """
        request = testing.DummyRequest()
        self.task1 = Task.query.filter(Task.name == self.task1.name).first()
        request.params['task_id'] = self.task1.id
        request.params['resource_id'] = self.task1.resources[0].id
        request.params['start'] = "Fri, 01 Nov 2013 08:00:00 GMT"
        request.params['end'] = "Fri, 01 Nov 2013 17:00:00 GMT"

        self.task1.status = self.status_rts
        self.assertEqual(self.task1.status, self.status_rts)
        time_log.create_time_log(request)
        self.assertEqual(self.task1.status, self.status_wip)

    def test_creating_a_time_log_for_a_task_with_status_pending_review(self):
        """testing if an response with status code 200 will be returned when
        a time log for a task with status "pending review" has been created
        """
        request = testing.DummyRequest()
        self.task1 = Task.query.filter(Task.name == self.task1.name).first()
        self.task1.status = self.status_prev

        request.params['task_id'] = self.task1.id
        request.params['resource_id'] = self.task1.resources[0].id
        request.params['start'] = "Fri, 01 Nov 2013 08:00:00 GMT"
        request.params['end'] = "Fri, 01 Nov 2013 17:00:00 GMT"

        response = time_log.create_time_log(request)
        self.assertEqual(response.status_code, 200)

    def test_creating_a_time_log_for_a_task_with_status_completed(self):
        """testing if an error response will be returned when trying to create
        time log for a completed task
        """
        request = testing.DummyRequest()
        self.task1 = Task.query.filter(Task.name == self.task1.name).first()
        self.task1.status = self.status_cmpl

        request.params['task_id'] = self.task1.id
        request.params['resource_id'] = self.task1.resources[0].id
        request.params['start'] = "Fri, 01 Nov 2013 08:00:00 GMT"
        request.params['end'] = "Fri, 01 Nov 2013 17:00:00 GMT"

        response = time_log.create_time_log(request)
        self.assertEqual(response.status_code, 500)

    def test_creating_a_time_log_for_a_task_with_status_has_revision(self):
        """testing if the task status will be converted to wip when a time log
        is eneter for a task with status "has revision"
        """
        request = testing.DummyRequest()
        self.task1 = Task.query.filter(Task.name == self.task1.name).first()
        self.task1.status = self.status_hrev

        request.params['task_id'] = self.task1.id
        request.params['resource_id'] = self.task1.resources[0].id
        request.params['start'] = "Fri, 01 Nov 2013 08:00:00 GMT"
        request.params['end'] = "Fri, 01 Nov 2013 17:00:00 GMT"

        response = time_log.create_time_log(request)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.task1.status,
            self.status_wip
        )

    def test_creating_a_time_log_for_a_task_whose_dependending_tasks_already_has_time_logs(self):
        """testing if a HTTPServer error will be raised when a time log tried
        to be for a task whose depending tasks already has time logs created
        (This test should be in Stalker)
        """
        # create a new task
        task2 = Task(
            name='Test Task 2',
            project=self.proj1,
            depends=[self.task1],
            resources=[self.user1],
            schedule_timing=4,
            schedule_unit= 'd',
            schedule_model='effort',
            status_list=self.task_status_list
        )
        DBSession.add(task2)
        DBSession.flush()
        transaction.commit()

        # set the status of task1 to complete
        self.task1.status = self.status_cmpl
        # artificially update task2 status to rts
        task2.status = self.status_rts
        DBSession.flush()
        transaction.commit()

        # and now create time logs for task2
        request = testing.DummyRequest()
        request.params['task_id'] = task2.id
        request.params['resource_id'] = self.user1.id
        request.params['start'] = "Fri, 01 Nov 2013 08:00:00 GMT"
        request.params['end'] = "Fri, 01 Nov 2013 17:00:00 GMT"
        response = time_log.create_time_log(request)
        self.assertEqual(response.status_int, 200)
        DBSession.add(task2)
        DBSession.flush()
        transaction.commit()

        # now because task2 is depending on to the task1
        # and task2 has now started, entering any new time logs to task1
        # is forbidden
        request = testing.DummyRequest()
        request.params['task_id'] = self.task1.id
        request.params['resource_id'] = self.user1.id
        request.params['start'] = "Fri, 02 Nov 2013 08:00:00 GMT"
        request.params['end'] = "Fri, 02 Nov 2013 17:00:00 GMT"

        response = time_log.create_time_log(request)
        self.assertEqual(
            response.status_int, 500
        )

    def test_creating_a_time_log_for_a_task_whose_dependent_tasks_has_not_finished_yet(self):
        """testing if a HTTPServer error will be raised when a time log tried
        to be created for a Task whose dependent tasks has not finished yet
        """
        # create a new task
        task2 = Task(
            name='Test Task 2',
            project=self.proj1,
            depends=[self.task1],
            resources=[self.user1],
            schedule_timing=4,
            schedule_unit='d',
            schedule_model='effort',
            status_list=self.task_status_list
        )
        DBSession.add(task2)
        DBSession.flush()
        transaction.commit()

        # now because task2 is depending on to the task1
        # and task1 is not finished yet (where the status is not
        # set to Complete, we should expect an HTTPServerError()
        # to be raised
        request = testing.DummyRequest()
        request.params['task_id'] = task2.id
        request.params['resource_id'] = self.user1.id
        request.params['start'] = "Fri, 01 Nov 2013 08:00:00 GMT"
        request.params['end'] = "Fri, 01 Nov 2013 17:00:00 GMT"

        response = time_log.create_time_log(request)
        self.assertEqual(
            response.status_int, 500
        )

    def test_creating_a_time_log_for_a_leaf_task_will_set_its_parents_status_to_wip(self):
        """testing if the status of the parent task will turn to wip if time
        log is entered to a child task
        """
        # TODO: This is also testing some functionality from view.task, slit it
        # create two new task
        task0 = Task(
            name='Test Task 0',
            project=self.proj1,
            status_list=self.task_status_list
        )
        task1 = Task(
            name='Test Task 1',
            parent=task0,
            status_list=self.task_status_list
        )
        task2 = Task(
            name='Test Task 2',
            parent=task1,
            resources=[self.user1],
            status_list=self.task_status_list,
            status=self.status_rts
        )
        task3 = Task(
            name='Test Task 3',
            parent=task1,
            resources=[self.user1],
            status_list=self.task_status_list,
            status=self.status_rts
        )
        task4 = Task(
            name='Test Task 4',
            parent=task0,
            resources=[self.user1],
            status_list=self.task_status_list,
            status=self.status_rts
        )
        DBSession.add_all([task0, task1, task2, task3, task4])
        DBSession.commit()
        DBSession.flush()
        transaction.commit()

        self.assertEqual(task0.status, self.status_new)
        self.assertEqual(task1.status, self.status_new)
        self.assertEqual(task2.status, self.status_rts)
        self.assertEqual(task3.status, self.status_rts)
        self.assertEqual(task4.status, self.status_rts)

        # now add a time log for task3 through create_time_log view
        request = testing.DummyRequest()

        # patch get_logged_in_user
        admins = Group.query.filter(Group.name == 'admins').first()
        self.user1.groups.append(admins)
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(self.user1)
        m.count(1, 1000000000)
        m.replay()
        request.route_url = lambda x, id=1: 'view_user'

        request.params['task_id'] = task3.id
        request.params['resource_id'] = self.user1.id
        request.params['start'] = "Fri, 19 Nov 2013 08:00:00 GMT"
        request.params['end'] = "Fri, 19 Nov 2013 17:00:00 GMT"
        response = time_log.create_time_log(request)
        self.assertEqual(response.status_int, 200)

        # now expect to have the status of task1 to be wip
        self.assertEqual(task3.status, self.status_wip)
        self.assertEqual(task2.status, self.status_rts)
        self.assertEqual(task1.status, self.status_wip)
        self.assertEqual(task0.status, self.status_wip)
        self.assertEqual(task4.status, self.status_rts)

        request.params['task_id'] = task2.id
        request.params['resource_id'] = self.user1.id
        request.params['start'] = "Fri, 18 Nov 2013 08:00:00 GMT"
        request.params['end'] = "Fri, 18 Nov 2013 17:00:00 GMT"
        response = time_log.create_time_log(request)
        self.assertEqual(response.status_int, 200)

        # now expect to have the status of task1 to be wip
        self.assertEqual(task3.status, self.status_wip)
        self.assertEqual(task2.status, self.status_wip)
        self.assertEqual(task1.status, self.status_wip)
        self.assertEqual(task0.status, self.status_wip)
        self.assertEqual(task4.status, self.status_rts)

        # now request a review and approve the task2 and task3 and expect the
        # task1 status is complete
        from stalker_pyramid.views.task import request_review, review_task
        #request = testing.DummyRequest()
        request.matchdict['id'] = task2.id
        request.params['send_email'] = 0
        request.route_url = lambda x, id: 'localhost:6453/tasks/23/view'
        request.route_path = lambda x, id: '/tasks/23/view'

        response = request_review(request)
        self.assertEqual(response.status_int, 200)

        #request = testing.DummyRequest()
        request.matchdict['id'] = task3.id
        request.params['send_email'] = 0
        response = request_review(request)
        print response.body
        self.assertEqual(response.status_int, 200)

        self.assertEqual(task3.status, self.status_prev)
        self.assertEqual(task2.status, self.status_prev)
        self.assertEqual(task1.status, self.status_wip)
        self.assertEqual(task0.status, self.status_wip)
        self.assertEqual(task4.status, self.status_rts)

        # approve the task2
        request.matchdict['id'] = task2.id
        request.params['review'] = 'Approve'
        response = review_task(request)
        self.assertEqual(response.status_int, 200)

        # and except task1 is still wip
        self.assertEqual(task3.status, self.status_prev)
        self.assertEqual(task2.status, self.status_cmpl)
        self.assertEqual(task1.status, self.status_wip)
        self.assertEqual(task0.status, self.status_wip)
        self.assertEqual(task4.status, self.status_rts)

        # approve the task3
        request.matchdict['id'] = task3.id
        request.params['review'] = 'Approve'
        response = review_task(request)
        self.assertEqual(response.status_int, 200)

        # now check the statuses
        self.assertEqual(task3.status, self.status_cmpl)
        self.assertEqual(task2.status, self.status_cmpl)
        self.assertEqual(task1.status, self.status_cmpl)
        self.assertEqual(task0.status, self.status_wip)
        self.assertEqual(task4.status, self.status_rts)

    def test_deleting_time_log_for_a_task_with_status_complete(self):
        """testing if it is not allowed to delete a time log of a task with
        status completed
        """
        # TODO: This is also testing some functionality from view.task, slit it
        # create two new task
        task0 = Task(
            name='Test Task 0',
            project=self.proj1,
            status_list=self.task_status_list
        )
        task1 = Task(
            name='Test Task 1',
            parent=task0,
            status_list=self.task_status_list,
            resources=[self.user1]
        )
        task1.status = self.status_wip
        DBSession.add_all([task0, task1])
        DBSession.commit()
        DBSession.flush()
        transaction.commit()

        self.assertEqual(task0.status, self.status_new)
        self.assertEqual(task1.status, self.status_wip)

        # now add a time log for task3 through create_time_log view
        request = testing.DummyRequest()

        # patch get_logged_in_user
        admins = Group.query.filter(Group.name == 'admins').first()
        self.user1.groups.append(admins)
        m = mocker.Mocker()
        obj = m.replace("stalker_pyramid.views.auth.get_logged_in_user")
        obj(request)
        m.result(self.user1)
        m.count(1, 1000000000)
        m.replay()
        request.route_url = lambda x, id=1: 'view_user'

        request.params['task_id'] = task1.id
        request.params['resource_id'] = self.user1.id
        request.params['start'] = "Fri, 19 Nov 2013 08:00:00 GMT"
        request.params['end'] = "Fri, 19 Nov 2013 17:00:00 GMT"
        response = time_log.create_time_log(request)
        self.assertEqual(response.status_int, 200)

        # set it to complete
        task1.status = self.status_cmpl

        # now try to remove it
        request.matchdict['id'] = task1.time_logs[0].id
        response = time_log.delete_time_log(request)
        self.assertEqual(response.status_int, 500)
        self.assertEqual(
            response.body,
            'Error: You can not delete a TimeLog of a Task with status CMPL'
        )

