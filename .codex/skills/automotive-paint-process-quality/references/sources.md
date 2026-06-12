# Sources And Evidence Rules

Prefer official vendor documentation, standards, and primary research. Record instrument model/firmware and factory-specific manuals because vendor product behavior and field names vary.

## Official Vendor Sources

- BYK-mac i multi-angle color/effect measurement: https://www.byk-instruments.com/en-US/color/byk-mac-i
- BYK orange peel knowledge page: https://www.byk-instruments.com/en-US/support/knowledge/white-papers/appearance/orange-peel
- BYK wave-scan product/technology page: https://www.byk-instruments.com/en-US/appearance/wave-scan
- BYK viscosity measurement knowledge page: https://www.byk-instruments.com/en-US/support/knowledge/white-papers/physical-test/viscosity-measurement
- Fischer magnetic induction method, including DIN EN ISO 2178: https://www.helmut-fischer.com/applications/solutions/magnetic-induction-measuring-method
- Fischer amplitude-sensitive eddy-current method, including DIN EN ISO 2360: https://www.helmut-fischer.com/applications/solutions/amplitude-sensitive-eddy-current-method
- Dürr EcoRP4 painting robot: https://www.durr.com/en/products/paint-shop-application-technology/paint-robots-paint-machines/paint-robots-automotive/ecorp4
- Dürr DXQ Robotics path programming and simulation: https://www.durr.com/en/products/software-controls/dxq/robotics
- Dürr EcoBell official search/reference entry: https://www.durr.com/en/search?tx_solr%5Bq%5D=EcoBell

## Primary AI Sources

- XGBoost: A Scalable Tree Boosting System: https://doi.org/10.1145/2939672.2939785
- A Unified Approach to Interpreting Model Predictions (SHAP): https://papers.nips.cc/paper/7062-a-unified-approach-to-interpreting-model-predictions

## Evidence Rules

- Treat the PQ-AI 3C2B sequence as a factory business definition that must be confirmed during onboarding.
- Treat generic parameter-effect relationships as engineering hypotheses until verified for the exact Dürr atomizer/controller, robot path, material, and factory.
- Never copy numeric limits from public material into recommendation constraints. Use approved factory manuals, TDS/COA, and controlled trials.
- Mark inferred conclusions explicitly. Preserve source URI, version/date, and effective scope in governed master data.
