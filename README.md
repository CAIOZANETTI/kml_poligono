# KML Poligono - Terraplenagem

Sistema Streamlit para calculo de corte e aterro de poligonos importados via KML do Google Earth.

## Funcionalidades

- Upload de multiplos arquivos KML (poligonos do Google Earth)
- Elevacao automatica via **Copernicus DEM GLO-30** (30m, gratuito) com fallback Open-Meteo/OpenTopoData
- Calculo de volumes de corte e aterro pelo metodo de grade (DNIT 106/2009-ES, DNIT 108/2009-ES)
- Cota otima por bissecao (corte empolado = aterro compactado)
- Volumes de talude de corte e aterro nas bordas
- Volume de remocao vegetal separado
- Fatores DNIT por categoria de solo (1a, 2a, 3a categoria)
- Diagrama de Bruckner com DMT, DLT e zonas de transporte
- Relatorios HTML (gerencial + analitico) e planilha Excel

## Paginas

| Pagina | Descricao |
|---|---|
| Home | Upload KML, parametros, metricas por poligono |
| Curvas de Nivel | Mapa de contorno 2D com cota de projeto destacada |
| Terreno 3D | Surface com contornos, eixo Z relativo (corte/aterro) |
| Comparacao 3D | Terreno vs plataforma de projeto |
| Bruckner | Diagrama de massa, perfil de faixa, zonas de transporte |
| Tabela de Volumes | Resumo com totais e grafico de barras |
| Downloads | HTML gerencial, HTML analitico, Excel |

## Parametros ajustaveis

| Parametro | Default | Descricao |
|---|---|---|
| Espacamento da grade | 10 m | Distancia entre pontos internos |
| Remocao vegetal | 0.30 m | Camada organica removida |
| Talude de corte | 1H:1V (45 graus) | Inclinacao do talude de corte |
| Talude de aterro | 2H:1V (26.6 graus) | Inclinacao do talude de aterro |
| Categoria do solo | 1a Categoria | Fatores DNIT de empolamento/homogeneizacao |

## Fonte de elevacao

Cadeia de fallback automatica:

1. **Copernicus DEM GLO-30** - 30m, +-4m vertical, tiles AWS S3 gratuitos (missao TanDEM-X)
2. **Open-Meteo** - SRTM 90m via API REST
3. **OpenTopoData** - SRTM 30m via API REST
4. **Google Maps** - API paga (opcional, requer chave)

Para projeto executivo, recomenda-se importar KML com elevacao de levantamento topografico RTK (+-2cm).

## Stack

Python, Streamlit, Plotly, NumPy, SciPy, Shapely, utm, tifffile

## Como rodar

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Normas de referencia

- DNIT 106/2009-ES (Cortes)
- DNIT 108/2009-ES (Aterros)
- NBR 5681 (Controle tecnologico)
- DER/PR Manual de Terraplenagem 2023
