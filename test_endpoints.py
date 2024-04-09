from pprint import pprint
from gorzdrav.api import Gorzdrav
from models import pydantic_models
import json


districts: list[pydantic_models.ApiDistrict] = Gorzdrav.get_districts()
print(districts)

lpus: list[pydantic_models.ApiLPU] = Gorzdrav.get_lpus()
print(lpus)
with open(file="lpus.json", mode='w') as f:
    lpus_json = [lpu.model_dump() for lpu in lpus]
    json.dump(lpus, fp=f)

# specialties = {}
# for lpu in lpus:
    # specialties_lpu: list[pydantic_models.ApiSpecialty] = Gorzdrav.get_specialties(lpuId=lpu.id)
    # specialties[lpu.id] = [s. for s in specialties_lpu]
