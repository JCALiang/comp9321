
from mongoengine import StringField, IntField, FloatField, Document, EmbeddedDocument, ListField, MapField, EmbeddedDocumentField
import xlrd
import re
import csv


class Year(EmbeddedDocument):
    year = IntField(required=True)
    Number_of_incidents = IntField(required=True)
    Rate_per_100_000_population= FloatField(required=True)

    def __init__(self, year, Number_of_incidents, Rate_per_100_000_population, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.year = year
        self.Number_of_incidents=Number_of_incidents
        self.Rate_per_100_000_population = Rate_per_100_000_population


class OffenceType(EmbeddedDocument):
    offence_type=StringField(min_length=None)
    years = MapField(EmbeddedDocumentField(Year))
    _24_month_trend=StringField(min_length=None)
    _60_month_trend=StringField(min_length=None)
    LGA_ranking= StringField(min_length=None)

    def __init__(self, offence_type, years, _24_month_trend, _60_month_trend, LGA_ranking, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.offence_type= offence_type
        self.years= years
        self._24_month_trend= _24_month_trend
        self._60_month_trend= _60_month_trend
        self.LGA_ranking= LGA_ranking

class OffenceGroup(EmbeddedDocument):
    offencegroup = StringField(required=True)
    offencetypes = MapField(EmbeddedDocumentField(OffenceType))

    def __init__(self, offencegroup, offencetypes, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.offencegroup = offencegroup
        self.offencetypes = offencetypes

class Lga(Document):
    title = StringField(required=True)
    subtitle=StringField(required=True)
    district = StringField(required=True, primary_key=True)
    offencegroups = MapField(EmbeddedDocumentField(OffenceGroup))

    def __init__(self, title, subtitle, district, offencegroups, *args, **values):
        super().__init__(*args, **values)
        self.title = title
        self.subtitle = subtitle
        self.district = district
        self.offencegroups = offencegroups


def xlms2json(file, district):
    mega={}
    wb = xlrd.open_workbook(file)
    sheet = wb.sheet_by_index(0)

    years_range= re.findall(r'\d{4}',sheet.cell(0, 0).value)
    first_year=int(years_range[0])
    last_year= int(years_range[1])


    #get all offence group entries
    offence_index=[]
    for i in range(7,69):
        if sheet.cell(i, 0).value not in [None, ' ' , '']:
            offence_index.append(i)
    offence_index.append(offence_index[-1]+1)
    print(offence_index)

    total_groups={}
    #offence group_level
    for i in range(len(offence_index)-1):
        offence_groups={}
        init=offence_index[i]
        end= offence_index[i+1]
        group_name=sheet.cell(init, 0).value
        group_name=str(group_name)
        
        total_types={}
        #offence type level
        for j in range(init, end):
            offence_name=sheet.cell(j, 1).value
            if offence_name  in [None, '', ' ']:
                offence_name=group_name
            offence_name=str(offence_name)
            c_count=1

            #year level
            total_year={}
            for year in range(first_year, last_year+1):
                total_year[str(year)]=Year(year, sheet.cell(j,c_count+1).value, sheet.cell(j, c_count+2).value)
                c_count+=2


            total_types[offence_name]=OffenceType(offence_name, total_year, 
                str(sheet.cell(j, c_count+1).value), 
                str(sheet.cell(j, c_count+2).value), 
                str(sheet.cell(j, c_count+3).value))

        
        total_groups[group_name]=OffenceGroup(group_name, total_types)

    document= Lga(sheet.cell(0,0).value, sheet.cell(2,0).value, district, total_groups)

    return document


def postcode_dict():
    postcode={}
    lga=[]
    with open('postcode.csv', 'r') as f:
        for line in f:
            if "New South Wales" in line:
                state, district, code= line.rstrip().split(',')
                code=int(code)
                district=district.lower().split()
                district="".join(district)
                if code not in postcode:
                    postcode[code]=[district.lower()]
                else:
                    postcode[code].append(district.lower())
                if district not in lga:
                    lga.append(district)
    return postcode, lga

