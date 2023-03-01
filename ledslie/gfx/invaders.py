char_mapping = {
    "+": 0xff,
    ".": 0x00,
}

def xmp_to_bytearray(xpm):
    r = []
    for row in xpm:
        r.append(bytearray(list(map(char_mapping.get, row))))
    return r

invader1f1_xpm = [
    "..+..+..",
    "...++...",
    "..++++..",
    ".+.++.+.",
    "++++++++",
    "+.++++.+",
    "+.+..+.+",
    "...++..."]


invader1f2_xpm = [
    "..+..+..",
    "+..++..+",
    "+.++++.+",
    "++.++.++",
    "++++++++",
    ".++++++.",
    "..+..+..",
    ".+....+."]

invader1 = [xmp_to_bytearray(invader1f1_xpm), xmp_to_bytearray(invader1f2_xpm)]

invader2f1_xpm = [
    "..++++..",
    ".++++++.",
    "++++++++",
    "+..++..+",
    "++++++++",
    ".++..++.",
    "+..++..+",
    ".+....+."]

invader2f2_xpm = [
    "..++++..",
    ".++++++.",
    "++++++++",
    "+..++..+",
    "++++++++",
    ".++..++.",
    "++.++.++",
    "+......+"]

invader2 = [xmp_to_bytearray(invader2f1_xpm), xmp_to_bytearray(invader2f2_xpm)]

invader3f1_xpm = [
    "...++...",
    "..++++..",
    ".++++++.",
    "++.++.++",
    "++++++++",
    "..+..+..",
    ".+.++.+.",
    "+.+..+.+"]

invader3f2_xpm = [
    "...++...",
    "..++++..",
    ".++++++.",
    "++.++.++",
    "++++++++",
    ".+.++.+.",
    "+......+",
    ".+....+."]

invader3 = [xmp_to_bytearray(invader3f1_xpm), xmp_to_bytearray(invader3f2_xpm)]
