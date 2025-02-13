"""
wxtcli - workspace.py
David Rice

Workspace module
"""
import typer
import csv
from wxcli.console import console
from wxcli.api import api_req
from wxcli.helpers.formatting import table_with_columns

app = typer.Typer()


@app.command()
def list_workspace_callerid(
    location_name: str = typer.Option(None, help="Webex Calling Location Name"),
    org_id: str = typer.Option(None, help="Organization ID"),
):
    """
    List Workspace CallerID settings for all workspaces (in an org, if specified)
    """

    orgId = None
    if org_id is not None:
        orgId = api_req(f"organizations/{org_id}")["id"]

    numbers = []
    if orgId is not None:
        numbers = api_req(
            "telephony/config/numbers",
            params={
                "orgId": orgId,
                "ownerType": "PLACE",
            },
        )
    else:
        numbers = api_req(
            "telephony/config/numbers",
            params={
                "ownerType": "PLACE",
            },
        )

    table = table_with_columns(
        ["Workspace", "Extension", "DID", "CallerID-Number", "CallerID-Name"],
        title="Workspace Info",
    )

    for number in numbers:
        workspaceId = number["owner"]["id"]
        workspaceFirstName = number["owner"]["firstName"]
        callerIdNumber = ""
        callerIdName = ""

        if orgId is not None:
            callerIdInfo = api_req(
                f"workspaces/{workspaceId}/features/callerId",
                params={
                    "orgId": orgId,
                },
            )
        else:
            callerIdInfo = api_req(f"workspaces/{workspaceId}/features/callerId")

        match callerIdInfo["selected"]:
            case "DIRECT_LINE":
                callerIdNumber = callerIdInfo["directNumber"]
            case "LOCATION_NUMBER":
                callerIdNumber = callerIdInfo["locationNumber"]
            case "CUSTOM":
                callerIdNumber = callerIdInfo["customNumber"]

        match callerIdInfo["externalCallerIdNamePolicy"]:
            case "DIRECT_LINE":
                callerIdName = callerIdInfo["displayName"]
            case "LOCATION_NUMBER":
                callerIdName = callerIdInfo["locationExternalCallerIdName"]
            case "OTHER":
                callerIdName = callerIdInfo["customExternalCallerIdName"]

        table.add_row(
            workspaceFirstName,
            number["extension"] if "extension" in number.keys() else "N/A",
            number["phoneNumber"] if "phoneNumber" in number.keys() else "N/A",
            callerIdNumber,
            callerIdName,
        )

    console.print(table)


@app.command()
def update_workspace_callerid_csv(
    location_name: str = typer.Option(None, help="Webex Calling Location Name"),
    org_id: str = typer.Option(None, help="Organization ID"),
    csvfile: str = typer.Option(None, help="Path to CSV File"),
):
    if csvfile is None:
        console.log("Missing filename")
        return None

    orgId = None
    if org_id is not None:
        orgId = api_req(f"organizations/{org_id}")["id"]

    with open(csvfile) as f:
        reader = csv.DictReader(f)
        for row in reader:
            print("+" + row["CallerID-Number"])
            if orgId is not None:
                number = api_req(
                    "telephony/config/numbers",
                    params={
                        "orgId": orgId,
                        "extension": row["Extension"],
                    },
                )
            else:
                number = api_req(
                    "telephony/config/numbers",
                    params={
                        "extension": row["Extension"],
                    },
                )
            workspaceId = number[0]["owner"]["id"]
            if orgId is not None:
                callerIdInfo = api_req(
                    f"workspaces/{workspaceId}/features/callerId",
                    params={
                        "orgId": orgId,
                    },
                )
            else:
                callerIdInfo = api_req(f"workspaces/{workspaceId}/features/callerId")

            match callerIdInfo["selected"]:
                case "DIRECT_LINE":
                    callerIdNumber = callerIdInfo["directNumber"]
                case "LOCATION_NUMBER":
                    callerIdNumber = callerIdInfo["locationNumber"]
                case "CUSTOM":
                    callerIdNumber = callerIdInfo["customNumber"]
            print(callerIdNumber)

            if orgId is not None:
                callerIdInfo = api_req(
                    f"workspaces/{workspaceId}/features/callerId",
                    method="put",
                    json={
                        "selected": "CUSTOM",
                        "customNumber": "+" + row["CallerID-Number"],
                    },
                    params={
                        "orgId": orgId,
                    },
                )
            else:
                callerIdInfo = api_req(
                    f"workspaces/{workspaceId}/features/callerId",
                    method="put",
                    json={
                        "selected": "CUSTOM",
                        "customNumber": "+" + row["CallerID-Number"],
                    },
                )


def get_location_id(orgId, location):
    locationInfo = []
    if orgId is not None:
        locationInfo = api_req(
            "locations",
            params={
                "name": location,
                "orgId": orgId,
            },
        )
    else:
        locationInfo = api_req(
            "locations",
            params={
                "name": location,
            },
        )
    # print(f"locationInfo[0][id]={locationInfo[0]['id']}")
    return locationInfo[0]["id"]


def checkWorkspaceExists(orgId, displayName):
    if orgId is not None:
        res = api_req(
            "workspaces",
            params={
                "displayName": displayName,
                "orgId": orgId,
            },
        )
    else:
        res = api_req(
            "workspaces",
            params={
                "displayName": displayName,
            },
        )
    # console.log(res,)
    return len(res) > 0


@app.command()
def add_workspace_calling_csv(
    org_id: str = typer.Option(None, help="Organization ID"),
    csvfile: str = typer.Option(None, help="Path to CSV File"),
):
    if csvfile is None:
        console.log("Missing filename")
        return None

    orgId = None
    if org_id is not None:
        orgId = api_req(f"organizations/{org_id}")["id"]

    # print(f"orgId={orgId}")
    # print(f"org_id={org_id}")
    with open(csvfile) as f:
        reader = csv.DictReader(f)
        for row in reader:
            # print(f"Name={row['Name']}")
            locationId = get_location_id(orgId=orgId, location=row["Location"])
            displayName = row["Name"]
            if checkWorkspaceExists(orgId, displayName) == False:
                wxcData = {
                    "extension": row["Extension"],
                    "locationId": get_location_id(
                        orgId=orgId, location=row["Location"]
                    ),
                }
                if len(row["Direct Dial"]) == 10:
                    wxcData["phoneNumber"] = "+1" + row["Direct Dial"]
                if org_id is not None:
                    res = api_req(
                        "workspaces",
                        method="post",
                        json={
                            "displayName": displayName,
                            "orgId": orgId,
                            "type": "other",
                            "supportedDevices": "phones",
                            "calling": {
                                "type": "webexCalling",
                                "webexCalling": wxcData,
                            },
                        },
                    )
                else:
                    res = api_req(
                        "workspaces",
                        method="post",
                        json={
                            "displayName": displayName,
                            "type": "other",
                            "supportedDevices": "phones",
                            "calling": {
                                "type": "webexCalling",
                                "webexCalling": wxcData,
                            },
                        },
                    )

                print(f"res={res}")
            else:
                print(f"Workspace {displayName} exists. Skipping")
