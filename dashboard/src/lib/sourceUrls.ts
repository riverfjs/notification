import type { SeriesSpec } from "../charts/types";

export interface SourceLink {
  label: string;
  title: string;
  url: string;
}

const fred = (ids: string[]): SourceLink => ({
  label: "FRED",
  title: `FRED: ${ids.join(", ")}`,
  url: `https://fred.stlouisfed.org/graph/?id=${ids.join(",")}`,
});

const yahoo = (symbol: string): SourceLink => ({
  label: `Yahoo ${symbol.replace("%5E", "^")}`,
  title: `Yahoo Finance history: ${symbol.replace("%5E", "^")}`,
  url: `https://finance.yahoo.com/quote/${symbol}/history`,
});

const BLS_CPI: SourceLink[] = [{
  label: "BLS CPI",
  title: "BLS CPI-U official time series",
  url: "https://data.bls.gov/timeseries/CUSR0000SA0",
}, {
  label: "BLS Core CPI",
  title: "BLS CPI-U less food and energy official time series",
  url: "https://data.bls.gov/timeseries/CUSR0000SA0L1E",
}];

const BLS_PPI: SourceLink[] = [{
  label: "BLS PPI",
  title: "BLS PPI final demand official time series",
  url: "https://data.bls.gov/timeseries/WPSFD4",
}, {
  label: "BLS Core PPI",
  title: "BLS PPI final demand less foods and energy official time series",
  url: "https://data.bls.gov/timeseries/WPSFD49104",
}, {
  label: "BLS PPI ex F/E/T",
  title: "BLS PPI final demand less foods, energy, and trade services official time series",
  url: "https://data.bls.gov/timeseries/WPSFD49116",
}];

const BEA_PCE: SourceLink[] = [{
  label: "BEA NIPA M",
  title: "BEA official monthly NIPA release TXT",
  url: "https://apps.bea.gov/national/Release/TXT/NipaDataM.txt",
}];

const BEA_GDP: SourceLink[] = [{
  label: "BEA NIPA Q",
  title: "BEA official quarterly NIPA release TXT",
  url: "https://apps.bea.gov/national/Release/TXT/NipaDataQ.txt",
}];

const CENSUS_FTD: SourceLink[] = [{
  label: "Census FTD",
  title: "Census EITS FTD API examples; data calls require an API key",
  url: "https://api.census.gov/data/timeseries/eits/ftd/examples.html",
}];

const CENSUS_ADVM3: SourceLink[] = [{
  label: "Census ADVM3",
  title: "Census EITS ADVM3 API examples; data calls require an API key",
  url: "https://api.census.gov/data/timeseries/eits/advm3/examples.html",
}];

const FRED_SERIES: Record<string, Record<string, string[]>> = {
  "macro/rates": {
    ust_3m: ["DGS3MO"],
    ust_2y: ["DGS2"],
    ust_10y: ["DGS10"],
    fed_funds_eff: ["DFF"],
    curve_10y_2y: ["T10Y2Y"],
    curve_10y_3m: ["T10Y3M"],
  },
  "macro/credit_spread": {
    baa_10y_spread: ["BAA10Y"],
    aaa_10y_spread: ["AAA10Y"],
    vix: ["VIXCLS"],
    baa_aaa_quality: ["BAA10Y", "AAA10Y"],
    hy_oas_full: ["BAMLH0A0HYM2"],
  },
  "macro/inflation_monetary": {
    breakeven_5y: ["T5YIE"],
    breakeven_10y: ["T10YIE"],
    fwd_5y5y_infl: ["T5YIFR"],
    fed_funds_target: ["DFEDTAR", "DFEDTARU"],
  },
  "macro/jobs_monthly": {
    nonfarm_payrolls_k: ["PAYEMS"],
    unemployment_rate_pct: ["UNRATE"],
  },
  "macro/claims_weekly": {
    initial_claims_weekly: ["ICSA"],
  },
  "macro/personal_finance": {
    personal_income: ["PI"],
    real_disposable_income: ["DSPIC96"],
    personal_saving_rate_pct: ["PSAVERT"],
  },
  "macro/home_sales_prices": {
    new_home_sales_k: ["HSN1F"],
    existing_home_sales_k: ["EXHOSLUSM495S"],
    case_shiller_natl: ["CSUSHPINSA"],
  },
  "macro/vehicle_sales": {
    total_vehicle_sales_m: ["TOTALSA"],
    light_vehicle_sales_m: ["ALTSALES"],
    autos_m: ["LAUTOSA"],
    light_trucks_m: ["LTRUCKSA"],
  },
  "macro/retail": {
    retail_food_services: ["RSAFS"],
    retail_ex_autos: ["RSFSXMV"],
  },
  "macro/housing_supply": {
    building_permits_k: ["PERMIT"],
    housing_starts_k: ["HOUST"],
    months_supply_new: ["MSACSR"],
  },
  "macro/mfg_orders_pmi": {
    durable_goods_orders: ["DGORDER"],
    mfg_new_orders_total: ["AMTMNO"],
    philly_fed_mfg: ["GACDFSA066MSFRBPHI"],
    ny_fed_mfg: ["GACDISA066MSFRBNY"],
  },
  "macro/wei": {
    weekly_economic_index: ["WEI"],
  },
  "macro/copper_gold_ppi": {
    copper_usd_mt: ["PCOPPUSDM"],
    ppi_all_commod: ["PPIACO"],
    copper_gold_ratio: ["PCOPPUSDM"],
  },
  "macro/oil_gold_cpi": {
    wti_usd_bbl: ["DCOILWTICO"],
    cpi_all_urban: ["CPIAUCSL"],
    oil_gold_ratio: ["DCOILWTICO"],
  },
};

const SERIES_SOURCES: Record<string, SourceLink[]> = {
  "tickers/VIX:c": [yahoo("%5EVIX")],
  "macro/us_inflation_releases:cpi_headline": BLS_CPI,
  "macro/us_inflation_releases:cpi_headline_mom": BLS_CPI,
  "macro/us_inflation_releases:cpi_headline_yoy": BLS_CPI,
  "macro/us_inflation_releases:cpi_core": BLS_CPI,
  "macro/us_inflation_releases:cpi_core_mom": BLS_CPI,
  "macro/us_inflation_releases:cpi_core_yoy": BLS_CPI,
  "macro/us_inflation_releases:ppi_headline": BLS_PPI,
  "macro/us_inflation_releases:ppi_headline_mom": BLS_PPI,
  "macro/us_inflation_releases:ppi_headline_yoy": BLS_PPI,
  "macro/us_inflation_releases:ppi_core": BLS_PPI,
  "macro/us_inflation_releases:ppi_core_mom": BLS_PPI,
  "macro/us_inflation_releases:ppi_core_yoy": BLS_PPI,
  "macro/us_inflation_releases:ppi_core_ex_food_energy_trade": BLS_PPI,
  "macro/us_inflation_releases:ppi_core_ex_food_energy_trade_mom": BLS_PPI,
  "macro/us_inflation_releases:ppi_core_ex_food_energy_trade_yoy": BLS_PPI,
  "macro/us_inflation_releases:pce": BEA_PCE,
  "macro/us_inflation_releases:pce_mom": BEA_PCE,
  "macro/us_inflation_releases:pce_yoy": BEA_PCE,
  "macro/us_inflation_releases:core_pce": BEA_PCE,
  "macro/us_inflation_releases:core_pce_mom": BEA_PCE,
  "macro/us_inflation_releases:core_pce_yoy": BEA_PCE,
  "macro/us_growth_releases:real_gdp_qoq_saar": BEA_GDP,
  "macro/us_trade_orders:trade_balance_goods_services": CENSUS_FTD,
  "macro/us_trade_orders:durable_ex_transport_orders": CENSUS_ADVM3,
  "macro/us_trade_orders:durable_ex_transport_orders_mom": CENSUS_ADVM3,
  "macro/michigan_sentiment:sentiment": [{
    label: "UMich CSV",
    title: "University of Michigan official sentiment CSV",
    url: "https://www.sca.isr.umich.edu/files/tbcics.csv",
  }],
  "macro/michigan_sentiment:current_conditions": [{
    label: "UMich CSV",
    title: "University of Michigan official current conditions / expectations CSV",
    url: "https://www.sca.isr.umich.edu/files/tbciccice.csv",
  }],
  "macro/michigan_sentiment:expectations": [{
    label: "UMich CSV",
    title: "University of Michigan official current conditions / expectations CSV",
    url: "https://www.sca.isr.umich.edu/files/tbciccice.csv",
  }],
  "macro/michigan_sentiment:inflation_1y": [{
    label: "UMich CSV",
    title: "University of Michigan official inflation expectations CSV",
    url: "https://www.sca.isr.umich.edu/files/tbcpx1px5.csv",
  }],
  "macro/michigan_sentiment:inflation_5y": [{
    label: "UMich CSV",
    title: "University of Michigan official inflation expectations CSV",
    url: "https://www.sca.isr.umich.edu/files/tbcpx1px5.csv",
  }],
  "macro/fng:*": [{
    label: "CNN",
    title: "CNN Fear & Greed dataviz API",
    url: "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/2020-09-19",
  }],
  "macro/breadth_official:pct_above_ma20": [{
    label: "Barchart",
    title: "Barchart $S5TW: S&P 500 above 20-day MA",
    url: "https://www.barchart.com/stocks/quotes/$S5TW",
  }],
  "macro/breadth_official:pct_above_ma50": [{
    label: "Barchart",
    title: "Barchart $S5FI: S&P 500 above 50-day MA",
    url: "https://www.barchart.com/stocks/quotes/$S5FI",
  }],
  "macro/breadth_official:pct_above_ma200": [{
    label: "Barchart",
    title: "Barchart $S5TH: S&P 500 above 200-day MA",
    url: "https://www.barchart.com/stocks/quotes/$S5TH",
  }],
  "macro/breadth:*": [yahoo("SPY")],
  "macro/sector_strength:*": [yahoo("SPY")],
  "macro/aaii:*": [{
    label: "AAII",
    title: "AAII Sentiment Survey results",
    url: "https://www.aaii.com/sentimentsurvey/sent_results",
  }],
  "macro/naaim:*": [{
    label: "NAAIM",
    title: "NAAIM Exposure Index",
    url: "https://www.naaim.org/programs/naaim-exposure-index/",
  }],
  "macro/putcall:*": [{
    label: "CBOE",
    title: "CBOE archived put/call ratio files",
    url: "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/equitypc.csv",
  }],
  "macro/putcall_cboe:*": [{
    label: "CBOE",
    title: "CBOE daily options market statistics",
    url: "https://www.cboe.com/markets/us/options/market-statistics/daily",
  }],
  "macro/cot_sp500:*": [{
    label: "CFTC",
    title: "CFTC TFF Socrata API: E-MINI S&P 500",
    url: "https://publicreporting.cftc.gov/resource/gpe5-46if.json?contract_market_name=E-MINI%20S%26P%20500&$limit=10",
  }],
  "macro/cot_nasdaq100:*": [{
    label: "CFTC",
    title: "CFTC TFF Socrata API: NASDAQ MINI",
    url: "https://publicreporting.cftc.gov/resource/gpe5-46if.json?contract_market_name=NASDAQ%20MINI&$limit=10",
  }],
  "macro/cot_legacy:*": [{
    label: "CFTC",
    title: "CFTC Legacy Futures Only Socrata API",
    url: "https://publicreporting.cftc.gov/resource/6dca-aqww.json?$limit=10",
  }],
  "macro/ism_pmi:*": [{
    label: "MQL5",
    title: "MQL5 ISM Manufacturing PMI calendar",
    url: "https://www.mql5.com/en/economic-calendar/united-states/ism-manufacturing-pmi",
  }, {
    label: "YCharts",
    title: "YCharts US ISM Manufacturing PMI",
    url: "https://ycharts.com/indicators/us_pmi",
  }, {
    label: "DBnomics",
    title: "DBnomics ISM PMI API",
    url: "https://api.db.nomics.world/v22/series/ISM/pmi/pm?observations=1&format=json",
  }],
  "macro/copper_gold_ppi:copper_gold_ratio_daily": [{
    label: "Westmetall",
    title: "Westmetall LME copper cash settlement archive",
    url: "https://www.westmetall.com/en/markdaten.php?action=table&field=LME_Cu_cash",
  }, {
    label: "LBMA",
    title: "LBMA gold PM fix JSON",
    url: "https://prices.lbma.org.uk/json/gold_pm.json",
  }],
  "macro/copper_gold_ppi:copper_fut_usd_mt": [{
    label: "Westmetall",
    title: "Westmetall LME copper cash settlement archive",
    url: "https://www.westmetall.com/en/markdaten.php?action=table&field=LME_Cu_cash",
  }],
  "macro/copper_gold_ppi:copper_gold_ratio": [{
    label: "LBMA",
    title: "LBMA gold PM fix JSON",
    url: "https://prices.lbma.org.uk/json/gold_pm.json",
  }],
  "macro/oil_gold_cpi:oil_gold_ratio": [{
    label: "LBMA",
    title: "LBMA gold PM fix JSON",
    url: "https://prices.lbma.org.uk/json/gold_pm.json",
  }],
};

function sourceFor(csv: string, col: string): SourceLink[] {
  const out: SourceLink[] = [];
  const ids = FRED_SERIES[csv]?.[col];
  if (ids) out.push(fred(ids));
  out.push(...(SERIES_SOURCES[`${csv}:${col}`] ?? SERIES_SOURCES[`${csv}:*`] ?? []));
  return out;
}

export function sourceLinksForSeries(series: SeriesSpec[]): SourceLink[] {
  const links: SourceLink[] = [];
  for (const s of series) {
    links.push(...sourceFor(s.csv, s.col));
    if (s.append) links.push(...sourceFor(s.append.csv, s.append.col));
  }

  const fredIds = new Set<string>();
  const other: SourceLink[] = [];
  for (const link of links) {
    const m = link.title.match(/^FRED: (.+)$/);
    if (m) {
      for (const id of m[1].split(", ")) fredIds.add(id);
    } else {
      other.push(link);
    }
  }

  const grouped = fredIds.size ? [fred([...fredIds]), ...other] : other;
  return grouped.filter((link, i, arr) => arr.findIndex((x) => x.url === link.url) === i);
}
