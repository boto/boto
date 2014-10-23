import json
from pyquery import PyQuery as pq
import requests


class FetchError(Exception):
    pass


def fetch_endpoints():
    # We utilize what the Java SDK publishes as a baseline.
    resp = requests.get('https://raw2.github.com/aws/aws-sdk-java/master/src/main/resources/etc/regions.xml')

    if int(resp.status_code) != 200:
        raise FetchError("Failed to fetch the endpoints. Got {0}: {1}".format(
            resp.status,
            resp.body
        ))

    return resp.text


def parse_xml(raw_xml):
    return pq(raw_xml, parser='xml')


def build_data(doc):
    data = {}

    # Run through all the regions. These have all the data we need.
    for region_elem in doc('Regions').find('Region'):
        region = pq(region_elem, parser='xml')
        region_name = region.find('Name').text()

        for endp in region.find('Endpoint'):
            service_name = endp.find('ServiceName').text
            endpoint = endp.find('Hostname').text

            data.setdefault(service_name, {})
            data[service_name][region_name] = endpoint

    return data


def main():
    raw_xml = fetch_endpoints()
    doc = parse_xml(raw_xml)
    data = build_data(doc)
    print(json.dumps(data, indent=4, sort_keys=True))


if __name__ == '__main__':
    main()
