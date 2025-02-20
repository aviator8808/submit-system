import functools
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from .models import *

# These permission decorators follow a general API pattern,
# where keywords in the URLconf that are retrieved from
# the database are returned as extra kwargs entries.

def evalbase_login_required(view_func):
    '''A convenience wrapper around the Django login_required
    decorator, that specifies the arguments we use in EvalBase.
    '''
    return login_required(view_func,
                          redirect_field_name='next',
                          login_url=reverse_lazy('login'))


def user_is_member_of_org(view_func):
    '''Confirm that the request.user is a member of the org named
    by the kwargs 'org' and 'conf'
    kwargs: org, conf
    returns: _org
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'org' not in kwargs or 'conf' not in kwargs:
            raise Http404('No such org or conf')
        org = get_object_or_404(Organization,
                                shortname=kwargs['org'],
                                conference__shortname=kwargs['conf'])
        if (org.owner == request.user or
            org.members.filter(pk=request.user.pk).exists()):
            kwargs['_org'] = org
            return view_func(request, *args, **kwargs)
        raise PermissionDenied('User is not member of org')
    return wrapped_view


def user_owns_org(view_func):
    '''Confirm that the request.user is the owner of the org
    named by the kwarg 'org'.
    kwargs: org
    returns: _org
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'org' not in kwargs or 'conf' not in kwargs:
            raise Http404('No such org or conf')
        org = get_object_or_404(Organization,
                                shortname=kwargs['org'],
                                conference__shortname=kwargs['conf'])
        if (org.owner == request.user):
            kwargs['_org'] = org
            return view_func(request, *args, **kwargs)
        raise PermissionDenied('User is not org owner')
    return wrapped_view


def user_is_active_participant(view_func):
    '''Confirm that the request.user is a member of an org in the conf
    named by kwarg['conf'], and that the org has submitted at least one
    submission.
    kwargs: conf
    returns: _valid_orgs, _subs
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'conf' not in kwargs:
            raise Http404('No such conf')
        valid_orgs = (Organization.objects
                      .filter(conference__shortname=kwargs['conf'])
                      .filter(members__pk=request.user.pk))
        subs = (Submission.objects
                .filter(task__conference__shortname=kwargs['conf'])
                .filter(submitted_by_in=valid_orgs))
        if subs:
            kwargs['_valid_orgs'] = valid_orgs
            kwargs['_subs'] = subs
            return view_func(request, *args, **kwargs)
        raise PermissionDenied('User is not active participant')
    return wrapped_view


def user_is_participant(view_func):
    '''Confirm that the user is a member of an org registered to
    participate in the conf named by kwargs['conf'].  This is essentially
    the same permission as user_is_member_of_org, except there's
    no org in kwargs.
    kwargs: conf
    returns: _valid_orgs
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'conf' not in kwargs:
            raise Http404('No such conf')
        valid_orgs = (Organization.objects
                      .filter(conference__shortname=kwargs['conf'])
                      .filter(members__pk=request.user.pk))
        if valid_orgs:
            kwargs['_valid_orgs'] = valid_orgs
            return view_func(request, *args, **kwargs)
        raise PermissionDenied('User is not a member of a participating group')
    return wrapped_view


def user_may_edit_submission(view_func):
    '''Confirm that the request.user is either the submittor
    of the kwarg 'runtag' submitted to kwarg 'conf', or that
    the request.user is the owner of the group that submitted it.
    kwargs: conf, runtag
    returns: _sub
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'conf' not in kwargs or 'runtag' not in kwargs:
            raise Http404('No such conf or runtag')
        sub = get_object_or_404(Submission,
                                Q(task__conference__shortname=kwargs['conf']) &
                                Q(runtag=kwargs['runtag']))
        if (sub.submitted_by == request.user or
            request.user == sub.org.owner):
            kwargs['_sub'] = sub
            return view_func(request, *args, **kwargs)
        raise PermissionDenied('User may not edit submission')
    return wrapped_view


def conference_is_open(view_func):
    '''Confirm that the conference named in the kwarg 'conf' is not complete.
    kwargs: conf
    returns: _conf
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'conf' not in kwargs:
            raise Http404('No such conf')
        conf = get_object_or_404(Conference, shortname=kwargs['conf'])
        if not conf.complete:
            kwargs['_conf'] = conf
            return view_func(request, *args, **kwargs)
        raise PermissionDenied('Conference is not open')
    return wrapped_view


def task_is_open(view_func):
    '''Confirm that the task is still open for submissions.
    kwargs: conf, task
    returns: _conf, _task
    '''
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if 'conf' not in kwargs or 'task' not in kwargs:
            raise Http404('No such conf or task')
        conf = get_object_or_404(Conference, shortname=kwargs['conf'])
        task = get_object_or_404(Task, shortname=kwargs['task'], conference=conf)
        if task.task_open:
            kwargs['_conf'] = conf
            kwargs['_task'] = task
            return view_func(request, *args, **kwargs)
        raise PermissionDenied('Task is not open')
    return wrapped_view
