claude reescreva esse readme apos ler essa instrução

com base no https://github.com/CAIOZANETTI/kml-earthworks
faça um sistema semlhante, python streamlit, importando um kml
nesse sistema o kml é um poligo no minimo 3 ponto que ira formar uma area
precisamos pegar todos os pontos interno do poligono e default é distancia entre 1 metro mas pode se ajustado pelo usuario
pode carregar varios poligonos que são montados no google eath
o usuario delimita a cota_zero de cada um para fazer os volumes de corte e aterro
tem opção de cota_otima quando corte= aterro (considerando as condições de compactação e empolamento)
premissa de remocao_vegetal =0,30 ( mas pode ser ajustada pelo usuario)
talude de corte = 1/1, premissa e ajuste do usuario 
talude de aterro = 1/2, premissa e ajuste do usuario


a entregra sera graficos do plotly:
 - curvas de nivel no plano
 - delhade de um corte dos platos
 - 3d surfice do primitivo como o solo estado natural

tabela com 
