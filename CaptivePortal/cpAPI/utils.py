from pyrad.client import Client
from pyrad import dictionary
from pyrad import packet
from src.settings import BASE_DIR
import os
import logging

logger = logging.getLogger(__name__)


def disconnect(username, ip):
    attr = {
        "Framed-IP-Address": str(ip),
    }
    # create coa client
    client = Client(
        server=ADDRESS,
        secret=SECRET,
        dict=dictionary.Dictionary(
            os.path.join(BASE_DIR, "FreeRadiusDictionary", "dictionary")
        ),
    )
    # set coa timeout
    client.timeout = 30

    attributes = {k.replace("-", "_"): attr[k] for k in attr}
    # create disconnect coa request
    request = client.CreateCoAPacket(
        code=packet.DisconnectRequest, **attributes
    )

    # send request
    result = client.SendPacket(request)
    if result.code == packet.DisconnectACK:
        logger.info(
            "In sending COA everything is OK! user {0} and ip {1}".format(
                username, ip
            )
        )
        return True
    elif result.code == packet.DisconnectNAK:
        logger.info(
            "In sending COA I got NAK! user {0} and ip {1}".format(
                username, ip
            )
        )
        return False
    else:
        logger.error(
            "In sending COA Something Bad Happened! user {0} and ip {1}".format(
                username, ip
            )
        )
        return False
