# list all 500 S&P companies
for _ in range(100):
    print("|")
import earningscall
# from earningscall import get_sp500_companies
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
earningscall.api_key = os.environ.get("EARNING_CALL_API")

# list = []
# for company in get_sp500_companies():
#     symbols = company.company_info.symbol
#     list.append(symbols)

sp500 = [
    'MMM', 'AOS', 'ABT', 'ABBV', 'ACN', 'ADBE', 'AMD', 'AES', 'AFL', 'A',
    'APD', 'ABNB', 'AKAM', 'ALB', 'ARE', 'ALGN', 'ALLE', 'LNT', 'ALL', 'GOOGL',
    'GOOG', 'MO', 'AMZN', 'AMCR', 'AEE', 'AAL', 'AEP', 'AXP', 'AIG', 'AMT',
    'AWK', 'AMP', 'AME', 'AMGN', 'APH', 'ADI', 'ANSS', 'AON', 'APA', 'AAPL',
    'AMAT', 'APTV', 'ACGL', 'ADM', 'ANET', 'AJG', 'AIZ', 'T', 'ATO', 'ADSK',
    'AZO', 'AVB', 'AVY', 'AXON', 'BKR', 'BALL', 'BAC', 'BK', 'BBWI', 'BAX',
    'BDX', 'BRK-B', 'BBY', 'BIO', 'TECH', 'BIIB', 'BLK', 'BX', 'BA', 'BMY',
    'AVGO', 'BR', 'BRO', 'BF-B', 'BLDR', 'BSX', 'BWA', 'BXP', 'CHRW', 'CDNS',
    'CZR', 'CPT', 'CPB', 'COF', 'CAH', 'KMX', 'CCL', 'CARR', 'CAT', 'CBOE',
    'CBRE', 'CDW', 'CE', 'COR', 'CNC', 'CF', 'CRL', 'SCHW', 'CHTR', 'CVX',
    'CMG', 'CB', 'CHD', 'CI', 'CINF', 'CTAS', 'CSCO', 'C', 'CFG', 'CLX',
    'CME', 'CMS', 'KO', 'CTSH', 'CL', 'CMCSA', 'CAG', 'COP', 'ED', 'STZ',
    'CEG', 'COO', 'CPRT', 'GLW', 'CTVA', 'CSGP', 'COST', 'CTRA', 'CCI', 'CSX',
    'CMI', 'CVS', 'DHI', 'DHR', 'DRI', 'DVA', 'DAY', 'DECK', 'DE', 'DAL',
    'DVN', 'DXCM', 'FANG', 'DLR', 'DFS', 'DG', 'DLTR', 'D', 'DPZ', 'DOV',
    'DOW', 'DTE', 'DUK', 'DD', 'EMN', 'ETN', 'EBAY', 'ECL', 'EIX', 'EW',
    'EA', 'ELV', 'LLY', 'EMR', 'ENPH', 'ETR', 'EOG', 'EPAM', 'EQT', 'EFX',
    'EQIX', 'EQR', 'ESS', 'EL', 'ETSY', 'EG', 'EVRG', 'ES', 'EXC', 'EXPE',
    'EXPD', 'EXR', 'XOM', 'FFIV', 'FDS', 'FICO', 'FAST', 'FRT', 'FDX', 'FIS',
    'FITB', 'FSLR', 'FE', 'FI', 'FMC', 'F', 'FTNT', 'FTV', 'FOXA', 'FOX',
    'BEN', 'FCX', 'GRMN', 'IT', 'GE', 'GEHC', 'GEV', 'GEN', 'GNRC', 'GD',
    'GIS', 'GM', 'GPC', 'GILD', 'GPN', 'GL', 'GDDY', 'GS', 'HAL', 'HIG',
    'HAS', 'HCA', 'DOC', 'HSIC', 'HSY', 'HES', 'HPE', 'HLT', 'HOLX', 'HD',
    'HON', 'HRL', 'HST', 'HWM', 'HPQ', 'HUBB', 'HUM', 'HBAN', 'HII', 'IBM',
    'IEX', 'IDXX', 'ITW', 'INCY', 'IR', 'PODD', 'INTC', 'ICE', 'IFF', 'IP',
    'IPG', 'INTU', 'ISRG', 'IVZ', 'INVH', 'IQV', 'IRM', 'JKHY', 'J', 'JNJ',
    'JCI', 'JPM', 'JNPR', 'K', 'KVUE', 'KDP', 'KEY', 'KEYS', 'KMB', 'KIM',
    'KMI', 'KLAC', 'KHC', 'KR', 'LHX', 'LH', 'LRCX', 'LW', 'LVS', 'LDOS',
    'LEN', 'LIN', 'LYV', 'LKQ', 'LMT', 'L', 'LOW', 'LULU', 'LYB', 'MTB',
    'MRO', 'MPC', 'MKTX', 'MAR', 'MMC', 'MLM', 'MAS', 'MA', 'MTCH', 'MKC',
    'MCD', 'MCK', 'MDT', 'MRK', 'META', 'MET', 'MTD', 'MGM', 'MCHP', 'MU',
    'MSFT', 'MAA', 'MRNA', 'MHK', 'MOH', 'TAP', 'MDLZ', 'MPWR', 'MNST', 'MCO',
    'MS', 'MOS', 'MSI', 'MSCI', 'NDAQ', 'NTAP', 'NFLX', 'NEM', 'NWSA', 'NWS',
    'NEE', 'NKE', 'NI', 'NDSN', 'NSC', 'NTRS', 'NOC', 'NCLH', 'NRG', 'NUE',
    'NVDA', 'NVR', 'NXPI', 'ORLY', 'OXY', 'ODFL', 'OMC', 'ON', 'OKE', 'ORCL',
    'OTIS', 'PCAR', 'PKG', 'PANW', 'PARA', 'PH', 'PAYX', 'PAYC', 'PYPL', 'PNR',
    'PEP', 'PFE', 'PCG', 'PM', 'PSX', 'PNW', 'PNC', 'POOL', 'PPG', 'PPL',
    'PFG', 'PG', 'PGR', 'PLD', 'PRU', 'PEG', 'PTC', 'PSA', 'PHM', 'QRVO',
    'PWR', 'QCOM', 'DGX', 'RL', 'RJF', 'RTX', 'O', 'REG', 'REGN', 'RF',
    'RSG', 'RMD', 'RVTY', 'ROK', 'ROL', 'ROP', 'ROST', 'RCL', 'SPGI', 'CRM',
    'SBAC', 'SLB', 'STX', 'SRE', 'NOW', 'SHW', 'SPG', 'SWKS', 'SJM', 'SNA',
    'SOLV', 'SO', 'LUV', 'SWK', 'SBUX', 'STT', 'STLD', 'STE', 'SYK', 'SMCI',
    'SYF', 'SNPS', 'SYY', 'TMUS', 'TROW', 'TTWO', 'TPR', 'TRGP', 'TGT', 'TEL',
    'TDY', 'TFX', 'TER', 'TSLA', 'TXN', 'TXT', 'TMO', 'TJX', 'TSCO', 'TT',
    'TDG', 'TRV', 'TRMB', 'TFC', 'TYL', 'TSN', 'USB', 'UBER', 'UDR', 'ULTA',
    'UNP', 'UAL', 'UPS', 'URI', 'UNH', 'UHS', 'VLO', 'VTR', 'VLTO', 'VRSN',
    'VRSK', 'VZ', 'VRTX', 'VTRS', 'VICI', 'V', 'VMC', 'WRB', 'GWW', 'WAB',
    'WBA', 'WMT', 'DIS', 'WBD', 'WM', 'WAT', 'WEC', 'WFC', 'WELL', 'WST',
    'WDC', 'WY', 'WHR', 'WMB', 'WTW', 'WYNN', 'XEL', 'XYL', 'YUM', 'ZBRA',
    'ZBH', 'ZTS', 'APP', 'DDOG', 'DOCU', 'HOOD', 'DASH', 'TKO', 'WSM', 'EME'
]


# using sets for comparing 

sp500 = set(sp500)
list = set(list)

print(f"companies in sp500 but not earningcall_api list {sp500 - list}")
print(f"companies in earningcall_api list but not sp500 {list - sp500}")

# sample_company = sp500[0]
# from earningscall import get_company

# # quarter = [1,2,3,4]
# # year = [2020,2021,2022,2023,2024,2025]
# company = get_company(sample_company)
# transcript = company.get_transcript(year=2021, quarter=3, level=2)

# # content = vars(transcript)
# # for key, value in content.items():
# #     print(f"{key}: {value}")

# # speaker_1 = transcript.speakers[0]
# # print(speaker_1)
# # print("speaker info")
# # print(f"what his name is {speaker_1.speaker}")
# # print(f"his name: {speaker_1.speaker_info.name}")
# # print(f"his title: {speaker_1.speaker_info.title}")
# # print(f"his text: {speaker_1.text}")

# row = []
# for speakers in transcript.speakers: 
#     if speakers.speaker_info is None:
#         print("no content for this speaker")
#     else: 
#         row.append({
#             'speaker_name': speakers.speaker_info.name,
#             'speaker_title': speakers.speaker_info.title,
#             'text': speakers.text
#         })
    
# df = pd.DataFrame(row)

# df.to_csv("tst.csv")