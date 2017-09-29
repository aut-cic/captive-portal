"""src URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

import requests
from django.conf.urls import url, include
# from django.contrib import admin
from django.db.models import Sum, F, Count
from cpAPI.models import Radacct, Radusergroup, Radpackages, Raddaily
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from django.views.decorators.cache import cache_page
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import  datetime
import xlsxwriter



def get_user_usage(username):
    # result = {}
    raddaily_record_monthly = Raddaily.objects.using('freeRadius').filter(username=username,
                                        createddate__lte=datetime.datetime.today().date(),
                                        createddate__gt=datetime.datetime.today().date() - datetime.timedelta(days=30))

    if raddaily_record_monthly:
        raddaily_record_weekly = raddaily_record_monthly.filter(
            createddate__lte=datetime.datetime.today().date(),
            createddate__gt=datetime.datetime.today().date() - datetime.timedelta(days=7))

        raddaily_record_daily = raddaily_record_monthly.filter(createddate=datetime.datetime.today().date())

        weekly_sum = raddaily_record_weekly.aggregate(weekly=Coalesce(Sum('usagediscount'), 0))
        monthly_sum = raddaily_record_monthly.aggregate(monthly=Coalesce(Sum('usagediscount'), 0))
        daily_sum = raddaily_record_daily.aggregate(daily=Coalesce(Sum('usagediscount'), 0))

        result = {
            'daily': daily_sum['daily'],
            'weekly': weekly_sum['weekly'],
            'monthly': monthly_sum['monthly']}
    else:
        result = {
            'daily': 0,
            'weekly': 0,
            'monthly': 0
        }
    return result

class UserUsageSerializerDaily(serializers.ModelSerializer):
    class Meta:
        model  =  Raddaily
        fields = ('username', 'usageorig' ,'usagediscount', 'createddate')

# class UserPeriodicusageSerializer(serializers.ModelSerializer):
#     class Meta:
#         model  =  Periodicusage
#         fields = ('username', 'periodic_usage', 'datetime')

class TopUsersSerializer(serializers.Serializer):
    order_by_choices = [('upload', 'upload'),
                        ('download', 'download'),
                        ('total', 'total')]
    upload = serializers.IntegerField(read_only=True)
    download = serializers.IntegerField(read_only=True)
    startdate = serializers.DateTimeField()
    stopdate = serializers.DateTimeField()
    orders = serializers.ChoiceField(order_by_choices, initial='download')


class TotalUsageSerializer(serializers.Serializer):
    upload = serializers.IntegerField(read_only=True)
    download = serializers.IntegerField(read_only=True)
    startdate = serializers.DateTimeField()
    stopdate = serializers.DateTimeField()


class GroupUsageSerializer(serializers.Serializer):
    group_choices = [('Msc', 'Msc'),
                        ('PhD', 'PhD'),
                        ('Students', 'Students'),
                     ('Faculty','Faculty'),
                     ('STAFF','STAFF')]
    upload = serializers.IntegerField(read_only=True)
    download = serializers.IntegerField(read_only=True)
    startdate = serializers.DateTimeField()
    stopdate = serializers.DateTimeField()
    group = serializers.ChoiceField(group_choices, initial='PhD')


# class UserUsageSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Userusage
#         fields = ('username', 'daily', 'weekly', 'monthly')

class UserUsageDaily(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        res = Raddaily.objects.using('freeRadius')\
                                    .filter(username=request.data['username'],
                                            createddate__gte=request.data['startdate'],
                                            createddate__lte=request.data['stopdate'])

        serializer = UserUsageSerializerDaily(res, many=True, context={'request': request})
        return Response(serializer.data)

# class UserHourlyUsage(APIView):
#     permission_classes = (AllowAny,)
#
#     def post(self, request):
#         if not request.data.get('total'):
#             res = Periodicusage.objects.using('freeRadius').filter(username=request.data['username'],
#                                                                    datetime__gte=request.data['startdate'],
#                                                                    datetime__lte=request.data['stopdate'])
#             serializer = UserPeriodicusageSerializer(res, many=True)
#             return Response(serializer.data)
#
#         else:
#             res =  Periodicusage.objects.using('freeRadius').filter(username=request.data['username'],
#                                                                     datetime__gte=request.data['startdate'],
#                                                                     datetime__lte=request.data['stopdate']) \
#                                                             .aggregate(usage=Sum('periodic_usage'))
#             return Response(res)

class TopUsers(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        usernames = Raddaily.objects.using('freeRadius').values('username')
        date_filter = usernames.filter(createddate__range=[request.data['startdate'],request.data['stopdate']])
        res = date_filter.annotate(usage_discount=Sum('usagediscount'),
                                   usage=Sum('usageorig')).order_by('-usage')[:30]
        return Response(res)


class TotalUsage(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        if not request.data['startdate'] or not request.data['stopdate']:
            pass
            # res = Periodicusage.objects.using('freeRadius') \
            #                     .aggregate(upload=Sum('acctinputoctets'),
            #                                download=Sum('acctoutputoctets'),
            #                                total=Sum(F('acctinputoctets') + F('acctoutputoctets')))
        else:
            res = Raddaily.objects.using('freeRadius')\
                                 .filter(createddate__gte=request.data['startdate'],
                                         createddate__lte=request.data['stopdate'])\
                                 .aggregate(usage=Sum('usageorig'),
                                            usage_discount=Sum('usagediscount'))
        return Response(res)


class GroupUsage(APIView):
    serializer_class = GroupUsageSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        users = Radusergroup.objects.using('freeRadius').filter(groupname=request.data['group']).values('username')
        result = Radacct.objects.using('freeRadius')\
                                .filter(username__in=users,
                                        acctstarttime__range=[request.data['startdate'],
                                                              request.data['stopdate']])\
                                .aggregate(upload=Sum('acctinputoctets'),
                                           download=Sum('acctoutputoctets'),
                                           total=Sum(F('acctinputoctets') + F('acctoutputoctets')))
        return Response(result)



class ALAKI(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        if request.data.get('group') == 'guest':
            users = Radacct.objects.using('freeRadius').filter(acctstoptime__isnull=True, username='guest') \
                                                       .values('username').distinct()
        elif request.data.get('status') == "online":
            users_group = Radusergroup.objects.using('freeRadius').filter(groupname__contains=request.data['group'].split('-')[0])\
                                                                 .values('username')
            users = Radacct.objects.using('freeRadius').filter(acctstoptime__isnull=True, username__in=users_group)\
                                                        .values('username').distinct()

        else:
            users = Radusergroup.objects.using('freeRadius').filter(groupname=request.data['group']).values('username').distinct()
        # result = Raddaily.objects.using('freeRadius')\
        #                         .filter(username__in=users, username__contains=request.data.get('username',''))\
        #                         .order_by('-monthly')
        # paginator = PageNumberPagination()
        # result = paginator.paginate_queryset(result, request)
        posted_username = request.data.get('username', None)
        results = []
        if not posted_username:
            for user in users:
                res = get_user_usage(user['username'])
                res.update(user)
                results.append(res)
        # return paginator.get_paginated_response(UserUsageSerializer(result, many=True).data)
        # page = request.GET.get('page', 1)
        # paginator = Paginator(results, 30)
        # try:
        #     result = paginator.page(page)
        # except PageNotAnInteger:
        #     result = paginator.page(1)
        # except EmptyPage:
        #     result = paginator.page(paginator.num_pages)
        results = sorted(results, key=lambda x: x["daily"], reverse=True)
        return Response(results)
# class QuotaLog(APIView):
#     permission_classes = (AllowAny,)
#     def get(self, request):
#         logs = Log.objects.using('quotaLogs').all().order_by('-created_at')
#         paginator = PageNumberPagination()
#         result_page = paginator.paginate_queryset(logs, request)
#         serializer = LogSerializer(result_page, many=True)
#         return paginator.get_paginated_response(serializer.data)

@api_view()
@permission_classes((AllowAny, ))
def group_changed(request):
    result = []
    for pg in Radpackages.objects.using('freeRadius').all():
        if pg.groupname == 'group1':
            continue
        result.append({
            'groupname': pg.groupname,
            'count': [0, 0, 0, 0]
        })

    for user in Radusergroup.objects.using("freeRadius").all():
        orig_groupname = user.groupname.split('-')[0]
        if orig_groupname == 'group1':
            continue

        gp_index = [i for i, x in enumerate(result) if x['groupname'] == orig_groupname][0]

        if 'H1' in user.groupname:
            result[gp_index]['count'][1] += 1

        elif 'H2' in user.groupname:
            result[gp_index]['count'][2] += 1

        elif 'H3' in user.groupname:
            result[gp_index]['count'][3] += 1

        else:
            result[gp_index]['count'][0] += 1
    return Response(sorted(result, key=lambda x: x['groupname']))


@api_view()
@permission_classes((AllowAny, ))
def count_group_online(request):
    result = {}
    total = 0
    for pg in Radpackages.objects.using('freeRadius').all():
        if pg.groupname == 'group1':
            continue
        result[pg.groupname] = 0

    online_users = Radacct.objects.using('freeRadius').filter(acctstoptime__isnull=True).values('username')

    for groupname in result:

        cnt = Radusergroup.objects.using('freeRadius') \
            .filter(username__in=online_users, groupname__contains=groupname).values('username').count()

        result[groupname] = cnt
        total +=  cnt

    result["Guest"] = online_users.filter(username__in=["guest", "test"]).count()
    result["Total"] = result["Guest"] + total
    return Response(result)


@api_view(['GET',])
def account(request):
    username = request.GET.get('username')
    cookie = {'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1IjoiNThiMzFjYjM0YTQxNGEwMDFjNzU3ZTM5IiwicyI6IjU5YTNhNWI3Njk0NTJiMDAxMmI5Nzc1NiIsImlhdCI6MTUwMzg5NzAxNX0.7hIxCvXlEtzHeA6yao_i8Y9_6UULBTTMnMICktVGIos'}
    r = requests.get("https://account.aut.ac.ir/api/admin/find/" + username.lower(), cookies = cookie)
    return Response(r.json())


@api_view(['GET',])
def report_test(request):
    workbook = xlsxwriter.Workbook('Expenses01.xlsx')
    # base = datetime.datetime.today()
    base = datetime.datetime.today() - datetime.timedelta(days=3)
    base = base.replace(hour=0, minute=0, second=0, microsecond=0)
    date_list = [base - datetime.timedelta(days=x) for x in range(1, 31)]
    for group in ['Faculty', 'PhD', 'MSc', 'BSc', 'Staff', 'NetAdmin' ]:
    # for group in ['NetAdmin', ]:
        worksheet = workbook.add_worksheet(group)
        worksheet.write(0, 0, 'USERNAME')
        col = 1
        for date in date_list:
            worksheet.write(0, col, date.strftime('%Y-%m-%d'))
            col+=1
        col = 0
        row = 1
        for user in Radusergroup.objects.using('freeRadius').filter(groupname__contains=group).all():
            worksheet.write(row, col, user.username)
            col+=1
            for date in date_list:
                # res_rec = Dailyusage.objects.using('freeRadius').filter(username=user.username,created_date=date.replace(hour=0, minute=0, second=0, microsecond=0)).first()
                res_rec = Periodicusage.objects.using('freeRadius') \
                    .filter(username=user.username, datetime__gte=date,
                            datetime__lt=date + datetime.timedelta(days=1)) \
                    .aggregate(usage=Sum('periodic_usage'))
                if res_rec.get('usage'):
                    # worksheet.write(row, col, int(res_rec.daily_usage))
                    worksheet.write(row, col, int(res_rec['usage']))
                else:
                    worksheet.write(row, col, 0)
                col+=1
            row+=1
            col=0
    workbook.close()
    return  Response('OK')






urlpatterns = [
    url(r'^api/v1/', include('cpAPI.urls')),
    url(r'^usage/user/daily/$', UserUsageDaily.as_view()),
    # url(r'^usage/user/hourly/$', UserHourlyUsage.as_view()),
    url(r'^top/$', TopUsers.as_view()),
    url(r'^usage/total/$', TotalUsage.as_view()),
    url(r'^usage/group/$', GroupUsage.as_view()),
    url(r'^online/group/$', count_group_online),
    # url(r'^log/$', QuotaLog.as_view()),
    url(r'^groupchange/$', group_changed),
    url(r'^alaki/', ALAKI.as_view()),
    url(r'^account/$', account),
    url(r'^repost_test/$', report_test)
    # url(r'^admin/', admin.site.urls),

    # url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
