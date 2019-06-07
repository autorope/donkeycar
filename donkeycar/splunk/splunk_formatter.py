"""
Splunk Formatter
"""

import datetime
import os
from pythonjsonlogger import jsonlogger


class SplunkFormatter(
        jsonlogger.JsonFormatter):
    """SplunkFormatter"""

    fields_to_add = {}
    org_fields = {}
    host_id = os.getenv(
        'HOST_ID',
        'dc1')

    def set_fields(
            self,
            new_fields):
        """set_fields

        Change the fields that will be added in on
        a log

        :param new_fields: new fields to patch in
        """
        self.org_fields = {}
        self.fields_to_add = {}
        for k in new_fields:
            self.org_fields[k] = new_fields[k]
            self.fields_to_add[k] = new_fields[k]
    # end of set_fields

    def get_current_fields(
            self):
        """get_current_fields"""
        return self.fields_to_add
    # end of get_current_fields

    def updated_current_fields(
            self,
            update_fields):
        """updated_current_fields

        :param update_fields: dict with values for
                              updating fields_to_add
        """
        self.fields_to_add = {}
        for k in self.org_fields:
            self.fields_to_add[k] = self.org_fields[k]
        self.fields_to_add.update(update_fields)
    # end of updated_current_fields

    def add_fields(
            self,
            log_record,
            record,
            message_dict):
        """add_fields

        :param log_record: log record
        :param record: log message
        :param message_dict: message dict
        """
        super(
            SplunkFormatter,
            self).add_fields(
                log_record,
                record,
                message_dict)
        if not log_record.get('timestamp'):
            now = datetime.datetime.utcnow().strftime(
                '%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['timestamp'] = now
    # end of add_fields

    def format(
            self,
            record,
            datefmt='%Y:%m:%d %H:%M:%S.%f'):
        """format

        :param record: message object to format
        """
        message = {
            'time': record.created,
            'path': record.pathname,
            'message': record.getMessage(),
            'exc': None,
            'host_id': self.host_id,
            'logger_name': record.name
        }

        # try adding in any exception/stacktraces
        if record.exc_info and not message.get('exc'):
            message['exc'] = self.formatException(
                record.exc_info)
        if not message.get(
                'exc') and record.exc_text:
            message['exc'] = record.exc_text

        log_record = {}
        try:
            log_record = OrderedDict()
        except NameError:
            log_record = {}
        # end of try/ex

        message.update(
            self.fields_to_add)
        self.add_fields(
            log_record,
            record,
            message)
        use_log_record = self.process_log_record(
            log_record)
        return '{}{}'.format(
            self.prefix,
            self.jsonify_log_record(
                use_log_record))
    # end of format

# end of SplunkFormatter
