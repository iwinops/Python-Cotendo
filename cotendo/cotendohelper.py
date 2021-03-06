from lxml import etree
from BeautifulSoup import BeautifulSoup
from records import *

dns_tag_lookup = {
    'soa': SOARecord,
    'ns': NSRecord,
    'a': ARecord,
    'cname': CNAMERecord,
    'mx': MXRecord,
    'ptr': PTRRecord,
    'srv': SRVRecord,
    'txt': TXTRecord
    }

self_closing_tags = [
    'result'
    ]

class CotendoObject(object):
    def __init__(self, response):
        self.token = response[0]
        self._add_config(response[1])

    def _add_config(self, config):
        soup = BeautifulSoup(
            config, selfClosingTags=self_closing_tags)
        self._data = etree.XML(soup.prettify())

class CotendoDNS(CotendoObject):
    def __init__(self, response):
        super(CotendoDNS, self).__init__(response)
        self._entries = self._get_entries()
        self.sort()

    def _get_entries(self):
        records = self._data.getchildren()[0]
        record_list = []
        for record in records:
            # Do not show SOA/NS Records
            if record.tag in ['soa', 'ns', 'comment']:
                continue

            # Do not show comments
            if record.tag == etree.Comment:
                continue

            recordObj = dns_tag_lookup[record.tag](record)
            record_list.append(recordObj)

        return record_list

    def show(self):
        """This could use some love, it's currently here as reference"""
        for entry in self._entries:
            print "{'%s': %s, 'records': %s}" % (
                entry._record_type, entry.host, entry.records)
        print

    def add_record(self, record):
        """Add or update a given DNS record"""
        rec = self.get_record(record._record_type, record.host)
        if rec:
            rec = record
            for i,r in enumerate(self._entries):
                if r._record_type == record._record_type \
                        and r.host == record.host:
                            self._entries[i] = record
        else:
            self._entries.append(record)
        self.sort()
        return True

    def diff_record(self, record):
        """Return the removed and added diffs"""
        rec = self.get_record(record._record_type, record.host)
        if rec is not None and record is not None:
            return {'removed': tuple(set(rec.results) - set(record.results)),
                    'added': tuple(set(record.results) - set(rec.recults))}
        else:
            return False

    def get_record(self, dns_record_type, host):
        """Fetch a DNS record"""
        record_list = self._entries
        for record in record_list:
            if record._record_type == dns_record_type \
                    and record.host == host:
                return record
        return False

    def del_record(self, dns_record_type, host):
        """Remove a DNS record"""
        rec = self.get_record(dns_record_type, host)
        if rec:
            self._entries = list(set(self._entries) - set([rec]))
        return True

    def sort(self):
        unsorted = {
            'a': [],
            'cname': [],
            'mx': [],
            'ptr': [],
            'srv': [],
            'txt': []
        }
        for record in self._entries:
            if record._record_type in unsorted.keys():
                unsorted[record._record_type].append(record)

        for key in unsorted.keys():
            unsorted[key] = sorted(
                unsorted[key], key=lambda result: result.host)

        sorted_entries = []
        for key in ('a', 'cname', 'mx', 'ptr', 'txt'):
            for record in unsorted[key]:
                sorted_entries.append(record)

        self._entries = sorted_entries

    @staticmethod
    def CreateRecord(record_type, host, results):
        """
        Create a record of type (record_type) and fill it with the given
        dict of results
        """
        record_class = dns_tag_lookup[record_type]
        record = etree.Element("a")
        record.set("host", host)
        for params in results:
            result = etree.Element("result")
            for k,v in params.iteritems():
                result.set(k, v)
            record.append(result)

        return record_class(record)

    @property
    def config(self):
        """Create the finalized configuration"""
        root = etree.Element("xml")
        resource_records = etree.SubElement(root, "resource_records")

        # Append SOA and NS records
        resource_records.append(SOARecord()._etree)
        resource_records.append(NSRecord()._etree)

        # Append the rest
        for record in self._entries:
            resource_records.append(record._etree)

        return etree.tostring(root, encoding="utf-8",
                              pretty_print=True)

class CotendoCDN(CotendoObject):
    def entries(self):
        return etree.tostring(self._data)

class UnescapedText(unicode):
    def escape(self):
        return self
