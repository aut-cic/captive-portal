import datetime
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Radacct, Radusergroup, Radpackages, Radgroupreply, Raddaily
from .utils import disconnect
from django.db.models import Sum
from django.db.models.functions import Coalesce
import logging

logger = logging.getLogger(__name__)


def get_ip(request):
    """
    Returns the IP of the request,
    accounting for the possibility of being behind a proxy.
    """
    ip = request.META.get("HTTP_X_FORWARDED_FOR", None)
    if ip:
        # X_FORWARDED_FOR returns client1, proxy1, proxy2,...
        ip = ip.split(", ")[0]
    else:
        ip = request.META.get("REMOTE_ADDR", "")
    return ip


@api_view(["GET"])
def index(request):
    result = {}
    user_ip = get_ip(request)
    if not user_ip:
        return Response("Oh no! I can't get user IP")
    rad_record = (
        Radacct.objects.using("freeRadius")
        .values("username")
        .filter(framedipaddress=user_ip, acctstoptime__isnull=True)
        .first()
    )
    if not rad_record:
        return Response("ops! no user for this ip!")

    result["username"] = rad_record["username"]
    # What is user groupname?!
    user_groupname = (
        Radusergroup.objects.using("freeRadius")
        .filter(username=result["username"])
        .first()
    )
    if user_groupname:
        result["groupname"] = user_groupname.groupname
    else:
        result["groupname"] = None
        return Response("can't find {0}".format(result["username"]))

    # what is user speed
    user_speeds = (
        Radgroupreply.objects.using("freeRadius")
        .filter(
            groupname__contains=result["groupname"],
            attribute="Mikrotik-Rate-Limit",
        )
        .all()
    )

    result["speeds"] = {}
    if user_speeds:
        for speed in user_speeds:
            result["speeds"][speed.groupname] = speed.value

    # What is user packages
    package = (
        Radpackages.objects.using("freeRadius")
        .filter(groupname=result["groupname"])
        .first()
    )
    if package:
        result["package"] = {
            "daily": package.daily_volume,
            "weekly": package.weekly_volume,
            "monthly": package.monthly_volume,
        }

    # user usage
    raddaily_record = (
        Raddaily.objects.using("freeRadius")
        .filter(
            username=result["username"],
            createddate=datetime.datetime.today().date(),
        )
        .first()
    )
    raddaily_record_monthly = Raddaily.objects.using("freeRadius").filter(
        username=result["username"],
        createddate__lte=datetime.datetime.today().date(),
        createddate__gt=datetime.datetime.today().date()
        - datetime.timedelta(days=30),
    )
    raddaily_record_weekly = raddaily_record_monthly.filter(
        createddate__lte=datetime.datetime.today().date(),
        createddate__gt=datetime.datetime.today().date()
        - datetime.timedelta(days=7),
    )
    if raddaily_record:
        result["usage"] = {
            "daily": raddaily_record.usagediscount,
            "weekly": raddaily_record_weekly.aggregate(Sum("usagediscount")),
            "monthly": raddaily_record_monthly.aggregate(Sum("usagediscount")),
        }

    result["sessions"] = []

    for session in (
        Radacct.objects.using("freeRadius")
        .filter(username=result["username"], acctstoptime__isnull=True)
        .all()
    ):
        result["sessions"].append(
            {
                "framedipaddress": session.framedipaddress,
                "acctstarttime": session.acctstarttime,
                "acctsessionid": session.acctsessionid,
                "acctuniqueid": session.acctuniqueid,
                "usage": session.acctinputoctets + session.acctoutputoctets,
            }
        )

    return Response(result)


@api_view(["POST", "GET"])
# @permission_classes((WhitelistPermission,))
def user_usage(request):
    result = {}
    if request.method == "POST":
        username = request.data.get("username")
        ip = request.data.get("ip")
    if request.method == "GET":
        username = request.GET.get("username", None)
        ip = request.GET.get("ip", None)
    if not username:
        rad_record = (
            Radacct.objects.using("freeRadius")
            .values("username")
            .filter(framedipaddress=ip, acctstoptime__isnull=True)
            .first()
        )
        if not rad_record:
            return Response("ops! no user for this ip!")

        username = rad_record["username"]

    result["username"] = username

    if result["username"] == "guest":
        result["groupname"] = "guest"
        result["usage"] = {"daily": 0, "weekly": 0, "monthly": 0}
        result["sessions"] = []
        for session in (
            Radacct.objects.using("freeRadius")
            .filter(
                username=result["username"],
                framedipaddress=ip,
                acctstoptime__isnull=True,
            )
            .all()
        ):
            result["sessions"].append(
                {
                    "framedipaddress": session.framedipaddress,
                    "acctstarttime": session.acctstarttime,
                    "acctsessionid": session.acctsessionid,
                    "acctuniqueid": session.acctuniqueid,
                    "usage": session.acctinputoctets
                    + session.acctoutputoctets,
                }
            )

        return Response(result)

    # What is user groupname?!
    user_groupname = (
        Radusergroup.objects.using("freeRadius")
        .filter(username=result["username"])
        .first()
    )
    if user_groupname:
        result["groupname"] = user_groupname.groupname

    else:
        result["groupname"] = None
        return Response("can't find {0}".format(username))

    # what is user speed
    user_speeds = (
        Radgroupreply.objects.using("freeRadius")
        .filter(
            groupname__contains=result["groupname"].split("-")[0],
            attribute="Mikrotik-Rate-Limit",
        )
        .all()
    )

    result["speeds"] = {}
    if user_speeds:
        for speed in user_speeds:
            result["speeds"][speed.groupname] = speed.value

    # What is user packages
    package = (
        Radpackages.objects.using("freeRadius")
        .filter(groupname__contains=result["groupname"].split("-")[0])
        .first()
    )
    if package:
        result["package"] = {
            "daily": package.daily_volume,
            "weekly": package.weekly_volume,
            "monthly": package.monthly_volume,
        }

    # user usage
    # usage = Userusage.objects.using('freeRadius').filter(username=result['username']).first()
    raddaily_record_monthly = Raddaily.objects.using("freeRadius").filter(
        username=result["username"],
        createddate__lte=datetime.datetime.today().date(),
        createddate__gt=datetime.datetime.today().date()
        - datetime.timedelta(days=30),
    )

    if raddaily_record_monthly:
        raddaily_record_weekly = raddaily_record_monthly.filter(
            createddate__lte=datetime.datetime.today().date(),
            createddate__gt=datetime.datetime.today().date()
            - datetime.timedelta(days=7),
        )

        raddaily_record_daily = raddaily_record_monthly.filter(
            createddate=datetime.datetime.today().date()
        )

        weekly_sum = raddaily_record_weekly.aggregate(
            weekly=Coalesce(Sum("usagediscount"), 0)
        )
        monthly_sum = raddaily_record_monthly.aggregate(
            monthly=Coalesce(Sum("usagediscount"), 0)
        )
        daily_sum = raddaily_record_daily.aggregate(
            daily=Coalesce(Sum("usagediscount"), 0)
        )

        result["usage"] = {
            "daily": daily_sum["daily"],
            "weekly": weekly_sum["weekly"],
            "monthly": monthly_sum["monthly"],
        }
    else:
        result["usage"] = {"daily": 0, "weekly": 0, "monthly": 0}
    # if raddaily_record:

    # else:
    #     result['usage'] = {
    #         'daily': 0,
    #         'weekly': weekly_sum['weekly'],
    #         'monthly': monthly_sum['monthly']
    #     }
    result["sessions"] = []

    for session in (
        Radacct.objects.using("freeRadius")
        .filter(username=result["username"], acctstoptime__isnull=True)
        .all()
    ):
        result["sessions"].append(
            {
                "framedipaddress": session.framedipaddress,
                "acctstarttime": session.acctstarttime,
                "acctsessionid": session.acctsessionid,
                "acctuniqueid": session.acctuniqueid,
                "usage": session.acctinputoctets + session.acctoutputoctets,
            }
        )

    # users reset times
    result["resetDate"] = datetime.datetime.today()

    dailyusagerecords = (
        Raddaily.objects.using("freeRadius")
        .filter(
            username=result["username"],
            createddate__lte=datetime.datetime.today().date(),
            createddate__gt=datetime.datetime.today().date()
            - datetime.timedelta(days=30),
        )
        .order_by("-createddate")
        .all()
    )

    result["usagehistory"] = []
    for record in dailyusagerecords:
        result["usagehistory"].append(
            {"created_date": record.createddate, "usage": record.usagediscount}
        )
    return Response(result)


@api_view(["POST", "GET"])
# @permission_classes((WhitelistPermission,))
def logout(request):
    if request.method == "POST":
        username = request.data.get("username")
        ip = request.data.get("ip")
        acctuniqueid = request.data.get("acctuniqueid")
    elif request.method == "GET":
        username = request.GET.get("username", None)
        ip = request.GET.get("ip", None)
        acctuniqueid = request.GET.get("acctuniqueid", None)
    else:
        return

    logging.info(
        "logout for user {} , ip {} and acctuniqueid {} ".format(
            username, ip, acctuniqueid
        )
    )

    rad_record = (
        Radacct.objects.using("freeRadius")
        .filter(
            username=username, framedipaddress=ip, acctuniqueid=acctuniqueid
        )
        .first()
    )
    if rad_record:
        if rad_record.acctstoptime:
            # TODO: it's mean that there is some problem
            logging.info(
                "logout for user {} and ip {}: user have stoptime.Why?".format(
                    username, ip
                )
            )
            return Response("OK")
        elif disconnect(username, ip):
            return Response("OK")
        else:
            # let's disconnect it again if fail
            logging.info(
                "logout for user {0} and ip {1}: Trying again!".format(
                    username, ip
                )
            )
            if not disconnect(username, ip):
                rad_record.acctstoptime = datetime.datetime.now()
                rad_record.save()

        return Response("OK")
    else:
        logging.info(
            "logout for user {0} and ip {1}: user not found!".format(
                username, ip
            )
        )
        return Response("OK")
