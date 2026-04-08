const { createClient } = require('@supabase/supabase-js');
require('dotenv').config({ path: 'backend/.env' });

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

async function main() {
  const { data: vehicles, error } = await supabase.from('fleet_management_view').select('brand, model, body_style, synthesis_data, base_price');
  if (error) {
     console.error("DB error", error);
     return;
  }
  
  function extractBodyType(v) {
    let raw = "";
    if (v.body_style) raw = v.body_style;
    else {
      const synth = v.synthesis_data;
      if (synth && synth.mapped_ai_data) {
        if (synth.mapped_ai_data.body_type) raw = synth.mapped_ai_data.body_type;
      }
    }
    if (!raw) return "";
    const low = raw.toLowerCase();
    if (low.includes("suv") || low.includes("crossover") || low.includes("sav")) return "SUV";
    return raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase();
  }

  function extractPower(v) {
    const synth = v.synthesis_data;
    const card = synth ? synth.card_summary : undefined;
    if (card && typeof card.power_hp === 'number') return card.power_hp;
    if (card && typeof card.power_hp === 'string') {
       const parsed = parseFloat(card.power_hp);
       if (!isNaN(parsed)) return parsed;
    }
    return 0; 
  }

  function parsePriceToNumber(raw) {
    if (!raw) return 0;
    if (typeof raw === 'number') return raw;
    const s = String(raw).replace(/\s/g, '').replace(/,/g, '.');
    const m = s.match(/[\d.]+/);
    if (m) {
      const p = parseFloat(m[0]);
      return isNaN(p) ? 0 : p;
    }
    return 0;
  }

  function getBasePrice(v) {
    return parsePriceToNumber(v.base_price);
  }

  const suvs = vehicles.filter(v => extractBodyType(v) === 'SUV');
  console.log(`Total SUVs:`, suvs.length);

  const powMin = Math.min(...vehicles.map(extractPower).filter(p => p > 0));
  const powMax = Math.max(...vehicles.map(extractPower).filter(p => p > 0));
  console.log(`Global Power range:`, powMin, powMax);

  const priceMin = Math.min(...vehicles.map(getBasePrice).filter(p => p >= 1000));
  const priceMax = Math.max(...vehicles.map(getBasePrice).filter(p => p >= 1000));
  console.log(`Global Price range:`, priceMin, priceMax);

  let hiddenByPower = 0;
  let hiddenByPrice = 0;
  let kept = 0;

  for (const v of suvs) {
    let hidePower = false;
    let hidePrice = false;

    const p = extractPower(v);
    if (p !== 0 && (p < powMin || p > powMax)) {
      hidePower = true;
    }

    const price = getBasePrice(v);
    if (price !== 0 && (price < priceMin || price > priceMax)) {
      hidePrice = true;
    }

    if (hidePower) hiddenByPower++;
    if (hidePrice) hiddenByPrice++;
    
    if (!hidePower && !hidePrice) kept++;
    else {
      console.log(`Hidden SUV: ${v.brand} ${v.model} - Power: ${p}, Price: ${price}`);
    }
  }

  console.log(`Kept: ${kept}, Hidden by Power: ${hiddenByPower}, Hidden by Price: ${hiddenByPrice}`);
}
main();
