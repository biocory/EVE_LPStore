import requests
import time
import logging
from copy import deepcopy

time.sleep(0.01)
todayDate = time.strftime("%Y%m%d", time.localtime())
logging.basicConfig(
        filename='.\\log\\eve_{}.log'.format(todayDate),
        level=logging.INFO,
        format='%(levelname)s:%(asctime)s:%(message)s'
)

JITA = 30000142
FORGE = 10000002


def getNPCorps():
    URL = "https://esi.evetech.net/v1/corporations/npccorps/"
    r = requests.get(URL)
    if r.status_code == 200:
        return r.json()

    logging.error(URL)
    logging.error("GET")
    logging.error(r.status_code)
    logging.error(r.headers)
    logging.error(r.text)
    return None


def getCorpInfo(corpID):
    URL = "https://esi.evepc.163.com/v3/corporations/{}/".format(corpID)
    r = requests.get(URL)
    if r.status_code == 200:
        return r.json()

    logging.error(URL)
    logging.error("GET")
    logging.error(r.status_code)
    logging.error(r.headers)
    logging.error(r.text)
    return None


def getLPStore(corpID):
    URL = "https://esi.evetech.net/v1/loyalty/stores/{}/offers/".format(corpID)
    r = requests.get(URL)
    logging.info(URL)
    if r.status_code == 200:
        return r.json()

    logging.error(URL)
    logging.error("GET")
    logging.error(r.status_code)
    logging.error(r.headers)
    logging.error(r.text)
    return None


def getCHName(IDs):
    URL = "https://esi.evepc.163.com/v2/universe/names/"
    r = requests.post(URL, data=str(IDs))
    if r.status_code == 200:
        return r.json()

    logging.error(URL)
    logging.error("POST")
    logging.error(str(IDs))
    logging.error(r.status_code)
    logging.error(r.headers)
    logging.error(r.text)
    return None


def getValue(id):
    URL = "https://www.ceve-market.org/api/market/region/"
    URL += "{}/system/{}/type/{}.json".format(FORGE, JITA, id)
    r = requests.get(URL)
    if r.status_code == 200:
        return r.json()

    logging.error(URL)
    logging.error("POST")
    logging.error(r.status_code)
    logging.error(r.headers)
    logging.error(r.text)
    return None


def getCorp(NPCorpsList):
    ids = set()
    NPCorps = {}
    DEL_list = []

    for NPCorpID in NPCorpsList:
        try:
            CorpInfo = getCorpInfo(NPCorpID)
            LPStore = getLPStore(NPCorpID)
        except Exception as E:
            logging.error(E)
        else:
            if CorpInfo is not None and LPStore is not None:
                NPCorps['{}'.format(NPCorpID)] = {
                    "info": CorpInfo,
                    "lp_store": LPStore
                }
                for item in LPStore:
                    ids.add(item["type_id"])
                    for required_item in item["required_items"]:
                        ids.add(required_item["type_id"])
            if LPStore is None or 0 == len(LPStore):
                DEL_list.append(NPCorpID)
    for NPCorpID in DEL_list:
        NPCorpsList.remove(NPCorpID)
        if '{}'.format(NPCorpID) in NPCorps:
            del NPCorps['{}'.format(NPCorpID)]

    logging.info("get NPC corp List Successed!")

    ids_list = []
    while len(ids) > 0:
        ids_list.append(ids.pop())
    return NPCorpsList, NPCorps, ids_list


def part_work(NPCorpsList):
    """获取军团LP兑换物品及其信息
        Args:
            NPCorpList: NPC军团id列表

        Returns:
            NPCorpList: 可以兑换物品的NPC军团id列表
                [123,124,125...244,245,246]
            NPCorps: 可以兑换物品的NPC军团信息字典,key为id
                [
                    '物品id': {
                        'info': {
                            "ceo_id": 3004049,
                            "corporation_description": "",
                            "corporation_name": "CBD社团",
                            "creator_id": 1,
                            "member_count": 0,
                            "tax_rate": 0,
                            "ticker": "CBDC",
                            "url": "None"
                        },
                        'lp_store': {
                            "isk_cost": 2400000,
                            "lp_cost": 2400,
                            "offer_id": 3584,
                            "quantity": 5000,
                            "required_items": [
                                {
                                    "quantity": 5000,
                                    "type_id": 234
                                }
                            ],
                            "type_id": 23047
                        },
                    }
                ]
            names: 物品信息字典,key为id
                {
                    "23047": {
                        "category": "inventory_type",
                        "id": 23047,
                        "name": "加达里海军铅质轨道弹 L",
                        "jita": {
                            "all": {
                                "max": 30000000,
                                "min": 0.01,
                                "volume": 8102161635
                            },
                            "buy": {
                                "max": 14.86,
                                "min": 0.01,
                                "volume": 2893652791
                            },
                            "sell": {
                                "max": 30000000,
                                "min": 15.23,
                                "volume": 5208508844
                            }
                        }
                    }
                }
    """
    NPCorpsList, NPCorps, ids_list = getCorp(NPCorpsList)
    if 0 == len(ids_list) or 0 == len(NPCorpsList):
        return None, None, None

    try:
        Names = []
        for i in range(0, len(ids_list), 255):
            Names += getCHName(ids_list[i: min(i + 255, len(ids_list))])
    except Exception as E:
        logging.error(E)
        return None, None, None
    logging.info("get Chinese Name Successed!")

    names = {}
    for name in Names:
        try:
            name["jita"] = getValue(name["id"])
        except Exception as E:
            logging.error(E)
        else:
            names["{}".format(name["id"])] = name
    logging.info("get Jita Market Successed!")

    return NPCorpsList, NPCorps, names


def write2file(filename, NPCorpsList, NPCorps, names):
    """将获得的lp兑换结果写入文件
        每lp价格计算公式: (吉他价*数量-兑换消耗isk)/数量
        需要物品的每lp价格计算公式：(吉他价*数量-兑换消耗isk-∑(依赖物品价格i*需要数量i))/数量
        输出格式
        军团名-物品名-isk花费-lp花费-数量-吉他收价-吉他卖价-收价折合isk-卖价折合isk-扣去购买素材后折合isk

        Args：
            filename: 文件名
            NPCorpList: 兑换物品的NPC军团id列表
            NPCorps: 兑换物品的NPC军团信息字典,key为id
            names: 物品信息字典,key为id

        Returns：
            没有返回值
    """
    with open(filename, "w+") as f:
        for NPCorpID in NPCorpsList:
            CorpInfo = NPCorps['{}'.format(NPCorpID)]["info"]
            LPStore = NPCorps['{}'.format(NPCorpID)]["lp_store"]
            for i, item in enumerate(LPStore):
                LPStore[i]["CHName"] =\
                    names["{}".format(item["type_id"])]["name"]
                f.write("{}\t{}\t{}\t{}\t{}\t".format(
                    CorpInfo["corporation_name"],
                    LPStore[i]["CHName"],
                    item["isk_cost"],
                    item["lp_cost"],
                    item["quantity"]
                    ))
                jitaValue = names["{}".format(item["type_id"])]["jita"]
                f.write("{}\t{}\t".format(
                    jitaValue["buy"]["max"],
                    jitaValue["sell"]["min"]
                ))

                required_items = item["required_items"]
                required_items_name_list = []
                total_isk = 0
                for required_item in required_items:
                    rid = required_item["type_id"]
                    rqu = required_item["quantity"]
                    ritem = names["{}".format(rid)]
                    required_items_name_list.append(
                        "{}*{}".format(ritem["name"], rqu))
                    isk_cost = rqu * ritem["jita"]["sell"]["min"]
                    if 0 >= isk_cost:
                        isk_cost = 9999999999999
                    total_isk += isk_cost

                if item["lp_cost"] > 0:
                    buyLP = \
                        ((jitaValue["buy"]["max"] * item["quantity"])
                            - item["isk_cost"]) / item["lp_cost"]
                    sellLP = \
                        ((jitaValue["sell"]["min"] * item["quantity"])
                            - item["isk_cost"]) / item["lp_cost"]
                    realLP = \
                        ((jitaValue["sell"]["min"] * item["quantity"])
                            - item["isk_cost"] - total_isk) / item["lp_cost"]
                else:
                    buyLP = 0
                    sellLP = 0
                    realLP = 0

                f.write("{}\t{}\t".format(
                    str(required_items_name_list), total_isk))
                f.write("{}\t{}\t{}\n".format(buyLP, sellLP, realLP))


def main():
    NPCorps_List = getNPCorps()
    for i in range(0, len(NPCorps_List), 10):
        logging.info(len(NPCorps_List))
        logging.info(i + 10)
        logging.info(i)
        NPCorpsList, NPCorps, names = \
            part_work(deepcopy(
                NPCorps_List[i: min(i + 10, len(NPCorps_List))]))
        if NPCorpsList is None:
            pass
        else:
            write2file(".\\lpstore\\lps{}_{}.txt".format(
                i, min(i + 10, len(NPCorps_List))),
                NPCorpsList, NPCorps, names)


if __name__ == "__main__":
    main()
