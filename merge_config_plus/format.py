import os


class MCPFormat:
    def __init__(self, file, base_dir, strip_prev=False):
        self.file = file
        self.base_dir = base_dir
        self.strip_prev = strip_prev

    def output(self, configs):
        for item in configs:
            if item[0] == "comment":
                if len(item[1]) == 0 or item[1][0] != "#":
                    print("#{line}".format(line=item[1]), file=self.file)
                continue

            name = item[1]
            if name.find("LOCAL_") == 0:
                continue

            if not self.strip_prev:
                # print previous values
                if len(item[2][0:-1]) > 0:
                    print("", file=self.file)

                for value in item[2][0:-1]:
                    print(
                        "# Previously {str} on {file}:{line}".format(
                            str=self.route(value),
                            file=os.path.relpath(value[3], self.base_dir),
                            line=value[2],
                        ),
                        file=self.file,
                    )

            # Actual last value
            value = item[2][-1]
            print(self.route(value, name), file=self.file)

    def route(self, value, name=None):
        if value[0] == "state":
            r = self.state(value[1], name)
        elif value[0] == "string":
            r = self.string(value[1], name)
        elif value[0] == "int":
            r = self.int(value[1], name)
        elif value[0] == "hex":
            r = self.hex(value[1], name)
        else:
            print("Internal error!")
            exit(1)
        return r.strip()

    def state(self, value, name=None):
        if name:
            if value == "n":
                return "# {name} is not set".format(name=name)
            else:
                return "{name}={value}".format(name=name, value=str(value))
        else:
            return "{value}".format(value=str(value))

    def string(self, value, name=None):
        if name:
            return '{name}="{value}"'.format(
                name=name, value=value.replace("\n", "\\n")
            )
        else:
            return '"{value}"'.format(value=value.replace("\n", "\\n"))

    def int(self, value, name=None):
        if name:
            return "{name}={value}".format(name=name, value=str(value))
        else:
            return "{value}".format(value=str(value))

    def hex(self, value, name=None):
        if name:
            return "{name}={value}".format(name=name, value=hex(value).upper())
        else:
            return "{value}".format(value=hex(value).upper())
