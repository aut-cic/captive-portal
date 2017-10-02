from pyrad.client import Client
from pyrad import dictionary
from pyrad import packet

# from src.settings import BASE_DIR
import os


def disconnect(ip):
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
    client.timeout = 10

    attributes = {k.replace("-", "_"): attr[k] for k in attr}
    # create disconnect coa request
    request = client.CreateCoAPacket(
        code=packet.DisconnectRequest, **attributes
    )

    # send request
    result = client.SendPacket(request)
    if result.code == 44:
        return True
    else:
        return False


disconnect("192.168.2.98")
