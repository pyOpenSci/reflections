import reflections


impact_list = reflections.datasources.citations.get_all_citations()

# drop astropy and sunpy
impact_list = [i for i in impact_list if i['package_name'].lower() != 'astropy']
impact_list = [i for i in impact_list if i['package_name'].lower() != 'sunpy']

def clean_nones(t_list):
    return [x for x in t_list if x is not None]

all_zen_cites = clean_nones([p['stats'].get('zenodo_citations') for p in impact_list])
all_zen_views = clean_nones([p['stats'].get('zenodo_views') for p in impact_list])
all_zen_downloads = clean_nones([p['stats'].get('zenodo_downloads') for p in impact_list])
all_zen_unique_views = clean_nones([p['stats'].get('zenodo_unique_views') for p in impact_list])
all_zen_unique_downloads = clean_nones([p['stats'].get('zenodo_unique_downloads') for p in impact_list])
all_joss_cites = clean_nones([p['stats'].get('joss_citations') for p in impact_list])
all_other_cites = clean_nones([p['stats'].get('other_citations') for p in impact_list])

print(f"Total packages: {len(impact_list)}")
print(f"Zenodo records: {len(all_zen_views)}")
print(f"JOSS records: {len(all_joss_cites)}")
print(f"Other records: {len(all_other_cites)}")

print(f"Zenodo citations: {sum(all_zen_cites)}")
print(f"Zenodo views: {sum(all_zen_views)}")
print(f"Zenodo downloads: {sum(all_zen_downloads)}")
print(f"Zenodo unique views: {sum(all_zen_unique_views)}")
print(f"Zenodo unique downloads: {sum(all_zen_unique_downloads)}")
print(f"JOSS citations: {sum(all_joss_cites)}")
print(f"Other citations: {sum(all_other_cites)}")

print(f"Zenodo median citations: {sorted(all_zen_cites)[len(all_zen_cites)//2]}")
print(f"Zenodo median views: {sorted(all_zen_views)[len(all_zen_views)//2]}")
print(f"Zenodo median downloads: {sorted(all_zen_downloads)[len(all_zen_downloads)//2]}")
print(f"Zenodo median unique views: {sorted(all_zen_unique_views)[len(all_zen_unique_views)//2]}")
print(f"Zenodo median unique downloads: {sorted(all_zen_unique_downloads)[len(all_zen_unique_downloads)//2]}")
print(f"JOSS median citations: {sorted(all_joss_cites)[len(all_joss_cites)//2]}")
print(f"Other median citations: {sorted(all_other_cites)[len(all_other_cites)//2]}")
