from xml.dom import minidom


class Parser:
    def __init__(self, filepath) -> None:
        self.filepath = filepath
        self._data = dict()

    def read_file(self):
        try:
            with open(self.filepath, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            print(f"File {self.filepath} not found")
            return
        except:
            print(f"An error occurred while reading the file {self.filepath}")
            return
        current_landscape = None
        for line in lines:
            if line.startswith('landscape:'):
                current_landscape = line.replace(
                    'landscape:', '').strip().upper()
                self._data[current_landscape] = {}
            elif line.startswith('user:'):
                users = line.replace('user:', '').strip().upper().split(',')
            else:
                hostname = line.strip()
                sid = hostname[6:9]
                instance = hostname[9:13]
                if not instance.startswith('db'):
                    print(f'Skipping {hostname}, Not a Database host.')
                    continue
                name = sid.upper()  # TODO
                if hostname.endswith('02'):
                    name += ' Secondary'
                if hostname[2:5] == "hbl":
                    hostname += ".sap.hi.hubbell-ad.com"
                self._data[current_landscape][name] = hostname


class HANA_Adder:
    BASE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<navigator version="1.2">
	<tree>
	</tree>
	<sapsystems>
	</sapsystems>
</navigator>"""

    def __init__(self) -> None:
        pass
