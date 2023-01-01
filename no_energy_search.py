

import TravelingCart
import SeedUtility
import TrashCans
from os import path
import sys
import json
from CSRandom import CSRandomLite as Random
import multiprocessing

import csv
from dataclasses import dataclass

import time

fairyItems = [254,256,258,260,376,421,268,262,266,270]

absolute_path = getattr(sys, '_MEIPASS', path.abspath(path.dirname(__file__)))
path_to_dat = path.abspath(path.join(absolute_path, 'RandomBundleSearchRange.txt'))
filename = path.abspath(path.join(absolute_path, 'CCRoomResults.txt'))
rangeFile = open(path_to_dat, 'r')
startRange = int(rangeFile.readline())
endRange = int(rangeFile.readline())
travelingCartCache = {}

#MIN_SEED = -2147483648
MIN_SEED = 0
MAX_SEED = 2147483647

SPRINKLER_ID = 599
QUALITY_SPRINKLER_ID = 621

#CART_DAYS = [5,7,12,14,19,21,26,28]
CART_DAYS = [5,7,12,14]

with open('RandomBundles.json', 'r') as f:
    randomBundleData = json.load(f)

seasonalIds = {
    "Hazelnut": 408,
    "Snow Yam": 416,
    "Crocus": 418,
    "Holly": 283,
    "Eggplant": 272,
    "Pumpkin": 276,
    "Summer Spangle": 593,
    "Fairy Rose": 595,
    "Sunflower": 421,
    "Tiger Trout": 699,
    "Walleye": 140,
    "Red Snapper": 150,
    "Poppy": 376,
    "Beet": 284,
    "Amaranth": 300,
    "Starfruit": 268,
    "Red Cabbage": 266,
    "Melon": 254,
    "Blueberry": 258,
    "Hot Pepper": 260,
    "Tomato": 256,
    "Wheat": 262
}


# duplicates of the Utility functions
def GetRandom(l, random):
    if l is None or len(l) == 0:
        return None
    return l[random.Next(len(l))]


def ParseItemList(items, pick, required, random):
    item_list = ParseRandomTags(items, random).split(',')
    if pick < 0:
        pick = len(item_list)
    if required < 0:
        required = pick
    while len(item_list) > pick:
        index_to_remove = random.Next(len(item_list))
        item_list.pop(index_to_remove)
    return item_list, required


def ParseRandomTags(data, random):
    open_index = 0
    while open_index != -1:
        open_index = data.rfind('[')
        if open_index != -1:
            close_index = data.find(']', open_index)
            if close_index == -1:
                return data
            #print(data, data[open_index+1:close_index])
            val = GetRandom(data[open_index+1:close_index].split('|'), random)
            data = data[:open_index] + val + data[close_index+1:]
            #print('\t',data)
    return data


def generate_random_bundle_names(seed, full=False):
    random = Random(seed*9)
    bundle_names = []

    for area_data in randomBundleData:
        index_lookups = []
        selected_bundles = {}

        # create keys for bundles to fill into
        for index_string in area_data['Keys'].strip().split(' '):
            index_lookups.append(int(index_string))

        # load the set bundles into their keys
        bundle_set = GetRandom(area_data['BundleSets'], random)
        if bundle_set != None:
            for bundle_data in bundle_set['Bundles']:
                selected_bundles[bundle_data['Index']] = bundle_data

        # build the random pool
        random_bundle_pool = []
        for bundle_data in area_data['Bundles']:
            random_bundle_pool.append(bundle_data)
        for i in range(len(index_lookups)):
            if i not in selected_bundles:
                index_bundles = []
                for bundle_data in random_bundle_pool:
                    if bundle_data['Index'] == i:
                        index_bundles.append(bundle_data)

                if not index_bundles:
                    for bundle_data in random_bundle_pool:
                        if bundle_data['Index'] == -1:
                            index_bundles.append(bundle_data)
                if index_bundles:
                    selected_bundle = GetRandom(index_bundles, random)
                    random_bundle_pool.remove(selected_bundle)
                    selected_bundles[i] = selected_bundle
        for key,val in selected_bundles.items():
            bundle_names.append(val['Name'])
            # color = val['Color'] if 'Color' in val else 'Green'
            # items,req = ParseItemList(val['Items'], val['Pick'], val['RequiredItems'], random)
            # if full:
            #     bundle_data = {
            #         'Name': val['Name'], 
            #         'Color': color, 
            #         'Required': req, 
            #         'Items': items, 
            #         'Reward': val['Reward'],
            #         'Sprite': val['Sprite'],
            #         'Index': val['Index']
            #     }
            # else:
            #     bundle_data = {
            #         'Name': val['Name'], 
            #         'Items': items, 
            #     }
            # bundleData[area_data['AreaName'] + '/'  + str(index_lookups[key])] = bundle_data
    return set(bundle_names)


def cleanupCache(seed):
    keys = []
    for key in travelingCartCache:
        if key < seed:
            keys.append(key)
    for key in keys:
        del travelingCartCache[key]


def displayDetails(seeds,cartDays,krobusDays):
        for seed in seeds:
            print(seed)
            print(json.dumps(generate_random_bundles(seed), indent=4))
            for day in cartDays:
                print(day)
                stock = TravelingCart.getTravelingMerchantStock_1_4(seed+day,"1.5")
                for item in stock.items():
                    print(SeedUtility.getItemFromIndex(item[0]))
            print("Krobus")
            for day in krobusDays:
                print(day)
                print(SeedUtility.getItemFromIndex( SeedUtility.uniqueKrobusStock(seed,day)))


@dataclass
class Result:
    seed: int


class SeedSearcher:
    def __init__(self, start_seed, chunk_size, parallel):
        self.seed = seed
        self.chunk_size = chunk_size
        self.parallel = parallel

    def save_progress(self):
        p = path.abspath(path.join(absolute_path, 'progress.txt'))
        with open(p, 'w') as f:
            f.write(str(self.seed))

    def load_progress(self):
        try:
            p = path.abspath(path.join(absolute_path, 'progress.txt'))
            with open(p, 'r') as f:
                self.seed = int(f.readline())
        except IOError:
            print('Starting from scratch!')
            self.seed = MIN_SEED

    def append_results(self, results):
        if len(results) == 0:
            return

        print(f'Saving {len(results)} valid seeds!')
        p = path.abspath(path.join(absolute_path, 'seeds.csv'))
        with open(p, 'a') as f:
            writer = csv.writer(f)
            for result in results:
                writer.writerow([result.seed])


    def process_chunk(self, seed_range):
        start, end = seed_range
        print(f'Processing {start} - {end}')
        results = []
        for seed in range(start, end):
            # bundles = generate_random_bundles(seed)
            # names = set([b['Name'] for k,b in bundles.items()])
            names = generate_random_bundle_names(seed)
            # names = set([b['Name'] for k,b in bundles.items()])

            if 'Exotic Foraging' not in names:
                continue
            if 'Rare Crops' not in names:
                continue
            if 'Garden' not in names:
                continue
            if 'Artisan' not in names:
                continue
            if "Adventurer's" not in names:
                continue
            if "Blacksmith's" not in names:
                continue
            if "Geologist's" not in names:
                continue

            sprinkler_day = None
            for day in CART_DAYS:
                stock = TravelingCart.getTravelingMerchantStock_1_4(seed+day,"1.5")
                if SPRINKLER_ID in stock:
                    num_sprinklers = stock[SPRINKLER_ID][1]
                    if num_sprinklers >= 2:
                        sprinkler_day = day
                if QUALITY_SPRINKLER_ID in stock:
                    sprinkler_day = day

            if sprinkler_day == None:
                continue

            results.append(Result(seed=seed))
        return results


    def search(self):
        while True:
            num_seeds = self.parallel*self.chunk_size
            next_seed = self.seed + num_seeds

            # If we don't have a full batch left, process last chunk
            if next_seed > MAX_SEED:
                results = self.process_chunk(self.seed, next_seed)
                self.seed = next_seed
                self.save_progress()
                print('DONE!')
                return

            # Prepare ranges for workers
            ranges = [(self.seed + self.chunk_size*(i),
                    self.seed + self.chunk_size*(i+1)) for i in range(self.parallel)]


            t0 = time.time()
            with multiprocessing.Pool(self.parallel) as pool:
                results = pool.map(self.process_chunk, ranges)
                for r in results:
                    self.append_results(r)

            t1 = time.time()

            total = t1-t0
            print(f'Processed {num_seeds} in {total} - {num_seeds/total} seeds/s')

            # Save progress
            self.seed = next_seed
            self.save_progress()


if __name__ == '__main__':
    seed = 12345
    # b = generate_random_bundles(seed)
    # print(b)

    # findSeed()

    search = SeedSearcher(0, 2**15, 8)
    search.load_progress()
    search.search()

    # seeds=[-186796577]
    # displayDetails(seeds,[5,7,12,14,19,21,26,28],[10,17,24])
