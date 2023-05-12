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
                self._data[current_landscape]["hosts"] = {}
            elif line.startswith('user:'):
                users = line.replace('user:', '').strip().upper().split(',')
                self._data[current_landscape]['users'] = users
            else:
                line = line.strip().split(':')
                hostname = line[0]
                tenants = None
                if len(line) > 1:
                    tenants = list(
                        map(lambda x: x.upper(), line[1:][0].split(',')))
                sid = hostname[6:9]
                instance = hostname[9:13]
                if not instance.startswith('db'):
                    print(f'Skipping {hostname}, Not a Database host.')
                    continue
                if hostname[2:5] == "hbl":
                    hostname += ".sap.hi.hubbell-ad.com"
                self._data[current_landscape]['hosts'][hostname] = [
                    sid.upper()]
                if tenants:
                    self._data[current_landscape]['hosts'][hostname].extend(
                        tenants)

    @property
    def data(self):
        return self._data


class HANA_Adder:
    SYSTEM_FORMAT = "{sid}:{hostname}:{instance_num}:{dbtype}:{user}"
    BASE_XML = '<?xml version="1.0" encoding="UTF-8"?><navigator version="1.2"><tree></tree><sapsystems></sapsystems></navigator>'

    def __init__(self) -> None:
        self.dom = minidom.parseString(self.BASE_XML)

    def createSapSystem(self, hostname: str, username: str, dbname: str = None, dbtype: str = "SYSTEMDB"):
        # main node
        sapsystem = self.dom.createElement("sapsystem")
        sid = hostname[6:9].upper()
        if dbtype == "USERDB":
            sapsystem.setAttribute("databasename", dbname)
        sapsystem.setAttribute("databasetype", dbtype)
        sapsystem.setAttribute(
            "description", f"{sid} System" if dbtype == "SYSTEMDB" else f"{dbname} Tenant")
        sapsystem.setAttribute("hostname", hostname)
        sapsystem.setAttribute("instancenumber", "0")
        sapsystem.setAttribute("open", "false")
        sapsystem.setAttribute("secure", "false")
        sapsystem.setAttribute("ssl", "false")
        sapsystem.setAttribute("systemname", sid)
        sapsystem.setAttribute("username", username)
        # sub nodes
        # hostroles hostname="icc1odcdhdb01" publicname="icc1odcdhdb01" role="CLIENT" sqlport="30015"
        hostrole = self.dom.createElement('hostrole')
        hostrole.setAttribute("hostname", hostname)
        hostrole.setAttribute("publicname", hostname)
        hostrole.setAttribute("role", "CLIENT")
        hostrole.setAttribute("sqlport", "30015")
        sapsystem.appendChild(hostrole)

        hostrole = self.dom.createElement('hostrole')
        hostrole.setAttribute("hostname", hostname.split('.')[0])
        hostrole.setAttribute("publicname", hostname.split('.')[0])
        hostrole.setAttribute("role", "MASTER")
        hostrole.setAttribute("sqlport", "0")
        sapsystem.appendChild(hostrole)
        # jdbc <jdbc locale="en_US" validate_crtf="true" />
        jdbc = self.dom.createElement('jdbc')
        jdbc.setAttribute("locale", "en_US")
        jdbc.setAttribute("validate_crtf", "true")
        sapsystem.appendChild(jdbc)
        # sapcontrol - in case of tenant <sapcontrol state="OFF" />
        if dbtype == "USERDB":
            sapcontrol = self.dom.createElement("sapcontrol")
            sapcontrol.setAttribute("state", "OFF")
            sapsystem.appendChild(sapcontrol)

        return sapsystem

    def run(self, data: dict, outfile: str) -> None:
        for landscape in data:
            users = data[landscape]['users']
            hosts = data[landscape]['hosts']
            folder = self.dom.createElement("folder")
            folder.setAttribute("name", landscape.upper())
            for user in users:
                for system in hosts:
                    # systemdb
                    # folder creation
                    systemdb = self.dom.createElement("sapsystem")
                    systemdb.setAttribute("name", self.SYSTEM_FORMAT.format(
                        sid=system[6:9], hostname=system, instance_num="00", dbtype="SYSTEMDB", user=user).upper())
                    folder.appendChild(systemdb)
                    # main data
                    systemdb = self.createSapSystem(system, user)
                    self.dom.getElementsByTagName("sapsystems")[
                        0].appendChild(systemdb)
                    # tenantdb
                    tenants = hosts[system]
                    # folder creation
                    tenantdb = self.dom.createElement("sapsystem")
                    tenantdb.setAttribute("name", self.SYSTEM_FORMAT.format(
                        sid=system[6:9], hostname=system + ":30015" if system.startswith("ichbl") else system, instance_num="00", dbtype=tenants[0], user=user).upper())
                    folder.appendChild(tenantdb)
                    # main data
                    tenantdb = self.createSapSystem(
                        hostname=system + ":30015" if system.startswith("ichbl") else system, username=user, dbname=tenants[0], dbtype="USERDB")
                    self.dom.getElementsByTagName("sapsystems")[
                        0].appendChild(tenantdb)
                    # additional tenantdb
                    for i in range(1, len(tenants)):
                        tenant = tenants[i]
                        tenantdb = self.dom.createElement("sapsystem")
                        tenantdb.setAttribute("name", self.SYSTEM_FORMAT.format(
                            sid=system[6:9], hostname=system + f":3004{i}" if system.startswith("ichbl") else system, instance_num="00", dbtype=tenant, user=user).upper())
                        folder.appendChild(tenantdb)
                        tenantdb = self.createSapSystem(hostname=system + f":3004{i}" if system.startswith(
                            "ichbl") else system, username=user, dbname=tenant, dbtype="USERDB")
                        self.dom.getElementsByTagName("sapsystems")[
                            0].appendChild(tenantdb)
            self.dom.getElementsByTagName("tree")[0].appendChild(folder)
        final = self.dom.toprettyxml()
        with open(outfile, 'w+') as f:
            f.write(final)


if __name__ == "__main__":
    parser = Parser('c1o_dbservers.txt')
    parser.read_file()
    print(parser.data)
    adder = HANA_Adder()
    adder.run(parser.data, outfile="c1o.xml")
