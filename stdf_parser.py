from datetime import datetime
import sys

# need a custom dictionary class to handle ranged entries
class CustomDictionary:
    def __init__(self, *args):
        self.single = {}
        self.ranges = []
        for argument in args:
            if isinstance(argument, dict):
                self.single.update(argument)
            elif isinstance(argument, tuple):
                if len(argument) == 2:
                    self.add_single_value(argument[0], argument[1])
                elif len(argument) == 3:
                    self.add_ranged_value(argument[0], argument[1], argument[2])
                else:
                    raise ValueError("Must be eitehr (key, value), or (start, end, value)")
            else:
                raise ValueError("Argument must be either dictionary or tuples.")

    def add_single_value(self, key, value):
        self.single[key] = value

    def add_ranged_value(self, start, end, value):
        self.ranges.append((start, end, value))

    def get(self, key=None):
        if key is not None:
            return self[key]
        return None

    def __getitem__(self, key):
        if key in self.single:
            return self.single.get(key)
        for start, end, value in self.ranges:
            if start <= key <= end:
                return value

    def __contains__(self, key):
        if key in self.single:
            return True
        for start, end, _ in self.ranges:
            if start <= key <= end:
                return True
        return False


FAR_CPU_TYPE = CustomDictionary({0: "DEC PDP-11 and VAX processors. F and D floating point..."},
                                {1: "Sun 1, 2, 3, and 4 computers."},
                                {2: "Sun 386i computers, and IBM PC"},
                                (3, 127, "Reserved by Teradyne"),
                                (128, 255, "Reserved by Customer"))

MIR_MODE_COD = CustomDictionary({'A': "AEL mode"},
                                {"C": "Checker mode"},
                                {"D": "D"}, {"E": "E"},{"M": "M"},{"P": "P"},{"Q": "Q"},
                                )


class ReadSTDF:
    def __init__(self, input_stdf):
        print("Reading ", input_stdf)
        self.file_path = input_stdf
        self.stdf = None
        self.byte_position = 0
        self.decode_record = {0: {10: "FAR", 20: "ATR"},
                               1: {10: "MIR", 20: "MRR", 30: "PCR", 40: "HBR", 50: "SBR",
                                   60: "PMR", 62: "PGR", 63: "PLR",
                                   70: "RDR", 80: "SDR"},
                               2: {10: "WIR", 20: "WRR", 30: "WCR"},
                               5: {10: "PIR", 20: self.decode_prr},
                               10: {30: "TSR"},
                               15: {10: "PTR", 15: "MPR", 20: "FTR"},
                               20: {10: "BPS", 20: "EPS"},
                               50: {10: "GDR", 30: "DTR"},
                               180: {0: "Reserved"},
                               181: {0: "Reserved"}}
        self.all_prr = {}
        self.max_x = self.max_y = -32767
        self.min_x = self.min_y =  32767

    def __enter__(self):
        self.stdf = open(self.file_path , 'rb')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.stdf:
            self.stdf.close()
            print(f"Closing {self.file_path}.")

    def read_byte(self, num_byte):
        data = self.stdf.read(num_byte)
        if bytes:
            self.byte_position += num_byte
            return data

    def seek(self, byte_position):
        if byte_position < 0:
            byte_position = 0
        self.stdf.seek(byte_position)
        self.byte_position = byte_position

    def read_header(self):
        data = self.read_byte(4)
        rec_len = int.from_bytes(data[:2], 'little')
        rec_typ = int.from_bytes(data[2:3], 'little')
        rec_sub = int.from_bytes(data[3:], 'little')
        return  rec_len, rec_typ, rec_sub

    @staticmethod
    def decode_far(data: bytes):
        print("File Attributes Record (FAR)")
        print(f"CPU_TYPE: {FAR_CPU_TYPE.get(data[0])}")
        print(f"STDF_VER: {data[1]}")

    @staticmethod
    def decode_atr(data: bytes):
        print("Audit Trail Record (ATR)")
        tim_mod = int.from_bytes(data[0:4], 'little')
        time_stamp = datetime.fromtimestamp(tim_mod).astimezone()
        print(f"STDF Modified on: {time_stamp} {time_stamp.tzname()}")
        print(f"CMD_LINE: {data[4:].decode()}")

    @staticmethod
    def decode_mir(data: bytes):
        print("Master Information Record (MIR)")
        setup_t = int.from_bytes(data[0:4], 'little')
        setup_t = datetime.fromtimestamp(setup_t).astimezone()

        start_t = int.from_bytes(data[4:8], 'little')
        start_t = datetime.fromtimestamp(start_t).astimezone()

        stat_num = data[8]

        mode_cod = chr(data[9])
        rtst_cod = chr(data[10])
        prot_cod = chr(data[11])
        burn_tim = int.from_bytes(data[12:14], 'little')
        cmod_cod = chr(data[14])
        data = data[15:]
        list_of_fields = ["LOT_ID", "PART_TYP", "NODE_NAM", "TSTR_TYP", "JOB_NAM", "JOB_REV", "SBLOT_ID", "OPER_NAM",
                        "EXEC_TYP", "EXEC_VER", "TEST_COD", "TST_TEMP", "USER_TXT", "AUX_FILE", "PKG_TYP", "FAMILY_ID",
                        "DATE_COD", "FLOOR_ID", "PROC_ID", "OPER_FRQ", "SPEC_NAM", "SPEC_VER", "FLOW_ID", "SETUP_ID",
                        "DSGN_REV", "ENG_ID", "ROM_COD", "SERL_NUM", "SUPR_NAM"]
        field_values = {}

        for field_name in list_of_fields:
            n = data[0]
            data = data[1:]
            field_values[field_name] = data[0:n].decode().strip()
            data = data[n:]

        print(f"Job setup:          {setup_t.ctime():<30} {setup_t.tzname()}")
        print(f"First test:         {start_t.ctime():<30} {start_t.tzname()}")
        print(f"Station #:          {stat_num}")
        print(f"station mode:       {mode_cod}")
        print(f"Tested before:      {rtst_cod}")
        print(f"Protect test data:  {prot_cod}")
        print(f"Burn-in time(min):  {burn_tim}")
        print(f"Command mode:       {cmod_cod}")

        for i, k in field_values.items():
            print(f"{i+':':20}{k}")

    def decode_pmr(self, data: bytes):
        pass

    def decode_rdr(self, data: bytes):
        pass

    @staticmethod
    def decode_sdr(data: bytes):
        print("Site Description Record (SDR)")
        site_count = data[2]
        field_values = {"HEAD_NUM": data[0], "SITE_GRP": data[1], "SITE_CNT": site_count}
        i = 0
        site_num = []
        while i < site_count:
            site_num.append(data[3 + i])
            i = i + 1
        data = data[3+i:]
        remaining_field_names = ["SITE_NUM", "HAND_TYP", "HAND_ID", "CARD_TYP", "CARD_ID",
                          "LOAD_TYP", "LOAD_ID", "DIB_TYP", "DIB_ID", "CABL_TYP", "CABL_ID", "CONT_TYP", "CONT_ID",
                          "LASR_TYP", "LASR_ID", "EXTR_TYP", "EXTR_ID"]
        i = 0
        while len(data) > 0:
            field_name = remaining_field_names[i]
            n = data[0]
            data = data[1:]
            field_values[field_name] = data[0:n].decode().strip()
            data = data[n:]
            i = i + 1
        for i, k in field_values.items():
            print(f"{i+':':20}{k}")

    def decode_prr(self, data: bytes):
        # print("Part Results Record (PRR)")
        x = int.from_bytes(data[9:11], "little", signed=True)
        y = int.from_bytes(data[11:13], "little", signed=True)
        field_values = {"HEAD_NUM": data[0], "SITE_GRP": data[1], "PART_FLG": data[2],
                        "NUM_TEST": int.from_bytes(data[3:5], "little"),
                        "HARD_BIN": int.from_bytes(data[5:7], "little"),
                        "SOFT_BIN": int.from_bytes(data[7:9], "little"),
                        "X_COORD": x,
                        "Y_COORD": y,
                        "TEST_T": int.from_bytes(data[13:17], "little"),
                        }
        data = data[17:]
        remaining_field_names = ["PART_ID", "PART_TXT", "PART_FIX"]
        i = 0
        while len(data) > 0:
            field_name = remaining_field_names[i]
            n = data[0]
            data = data[1:]
            field_values[field_name] = data[0:n].decode().strip()
            data = data[n:]
            i = i + 1
        if x < self.min_x:
            self.min_x = x
        elif x > self.max_x:
            self.max_x = x
        if y < self.min_y:
            self.min_y = y
        elif y > self.max_y:
            self.max_y = y
        self.all_prr[field_values["PART_ID"]] = {'x': x, 'y': y}


    def process(self):
        print("\nREC_LEN, REC_TYP, REC_SUB")
        while True:
            rec_len, rec_typ, rec_sub = self.read_header()
            if rec_len == 0:
                break
            print(f"{rec_len:7}, {rec_typ:7}, {rec_sub:7}")
            data = self.read_byte(rec_len)
            try:
                self.decode_record[rec_typ][rec_sub](data)
            except TypeError:
                continue
        self.show_part_results()

    def show_part_results(self):
        print("\nShowing Part Results Record\n")
        part_matrix = {}
        for part_id, coords in self.all_prr.items():
            x = coords.get('x')
            y = coords.get('y')
            print(f"x={x:6}   y={y:6}   part ID={part_id:>6}")
            if y not in part_matrix.keys():
                part_matrix[y] = {}
            part_matrix[y].update({x: part_id})
        self.print_part_grid(part_matrix)

    def print_part_grid(self, part_matrix):
        print("\nPart Results Grid View")
        print("     ", end="")
        for c in range(self.min_x-1, self.max_x+2, 1):
            print(f"{c:^5}", end="")
        print("\r")
        for row in range(self.max_y+1, self.min_y-2, -1):
            print(f"{row:^5}", end="")
            for col in range(self.min_x-1, self.max_x+2, 1):
                r = part_matrix.get(row)
                if r is not None:
                    part_id = r.get(col)
                else:
                    part_id = None
                if part_id is None:
                    part_id = " "
                print(f"{part_id:^5}", end="")
            print("\r")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Need to specify a STDF file like this: stdf_parser.py test_file.stdf")
    else:
        with ReadSTDF(sys.argv[1]) as stdf:
            stdf.process()


