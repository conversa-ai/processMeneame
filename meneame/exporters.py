from scrapy.exporters import BaseItemExporter

class MeneameExporter(BaseItemExporter):
    def __init__(self, file, **kwargs):
        super().__init__(**kwargs)
        self.file = file

    def export_item(self, item):
        serialized = self.serialize_field(item)
        self.file.write(serialized)