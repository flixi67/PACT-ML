from unstructured.partition.pdf import partition_pdf
# from unstructured.staging.base import convert_to_csv

elements = partition_pdf("data\pdfs\S_1995_444_UNPROFOR.pdf")

# isd_csv = convert_to_csv(elements)

for el in elements:
    print(el.category, ":", el.text)