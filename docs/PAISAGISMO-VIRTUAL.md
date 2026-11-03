# Atendimento paisagístico virtual e presencial

O portal apresenta o escopo de cada serviço, preparação, etapas, entregas e documentos antes de solicitar o orçamento. A contratação mantém o fluxo existente: solicitação → análise → proposta → aprovação → projeto. Não existe cobrança online nem contratação automática de um profissional externo.

## Fluxo implementado

1. O cliente escolhe **Paisagista virtual** ou **Paisagista presencial** no catálogo de serviços.
2. No planejador, informa endereço, largura/comprimento, orientação, luminosidade, solo, drenagem, manutenção, objetivos e observações.
3. Seleciona espécies da biblioteca ou importa plantas por CSV. JSON permite importar o levantamento completo exportado pelo planejador.
4. Distribui grupos de plantas pela posição X/Y, por campos ou arrastando os círculos. Cada marcador representa um grupo e sua quantidade; o diâmetro é uma representação no desenho.
5. Adiciona canteiros, caminhos, deck, gramado, construções ou água como áreas retangulares.
6. Visualiza a planta 2D com medidas, orientação e legenda, e pode baixar o SVG, os dados JSON e o memorial HTML imprimível em PDF pelo navegador.
7. Envia fotos e PDFs com a solicitação. Os anexos são privados; uma falha de upload preserva a solicitação já salva para evitar repetir sua criação.
8. A equipe prepara a proposta. Depois da aprovação, o projeto recebe os dados de levantamento, as espécies e a modalidade. Fotos e documentos da solicitação ficam disponíveis no projeto sem duplicação dos arquivos.

O cliente pode alterar o levantamento enquanto a solicitação está em Solicitação/Em análise. Uma proposta enviada ou encerrada bloqueia alterações do cliente. Revisões do projeto são realizadas pela equipe e protegidas por número de revisão; edições desatualizadas retornam conflito. O planejamento finalizado permanece protegido até uma revisão em manutenção.

## Importação

CSV UTF-8, vírgula ou ponto e vírgula, até 1 MB e 200 grupos. Identificação da espécie por nome popular, nome científico ou `species_id` existente.

```csv
especie;quantidade;x_m;y_m;diametro_m;aplicacao
Hibisco;6;2;3;1;Canteiro frontal
Lavanda;8;6;3;1;Bordadura
```

Use **Exportar dados** para obter o modelo JSON completo. O arquivo inclui `width`, `length`, `north`, `light`, `soil`, `drainage`, `maintenance`, `objective`, `notes`, `plantings` e `zones`. Limites: terreno até 500 × 500 m, 200 grupos e 100 áreas. Coordenadas e áreas são validadas contra os limites informados; espécies inexistentes, quantidades inválidas e arquivos malformados são rejeitados.

## Documentos e acesso

Fotos: JPG/PNG/WebP até 5 MB. Documentos: PDF até 10 MB. Somente o cliente vinculado e o administrador podem ler os anexos. O cliente não pode excluir documentos de entrega nem substituir os anexos depois de enviada a proposta. Não há publicação dos arquivos ou envio a terceiros.

## Escopo da visualização

A planta é uma prévia esquemática 2D baseada nas informações enviadas. Ela não calcula automaticamente espaçamentos agronômicos, viabilidade estrutural, relevo, hidráulica, custos de execução ou adequação climática completa. Medidas, locais de plantio e entregas técnicas são revisados pelo paisagista. Projetos antigos que já têm espécies preservam essas espécies quando a equipe inicia a planta visual.

## Pesquisa aplicada

- [RHS — levantamento do jardim](https://www.rhs.org.uk/garden-inspiration/design/get-to-know-your-garden): observar condições do local e registrar medidas antes do desenho.
- [University of Minnesota Extension — processo de projeto e seleção de plantas](https://extension.umn.edu/garden-and-home/yard-and-garden/lawns-and-landscapes-in-minnesota): necessidades do cliente, condições de cultivo, plano base, seleção e implantação/manutenção.
- [GARDENA — referência de planejador visual](https://www.gardena.com/ca-en/c/discover/mygarden-planning-tools/garden-planner): desenho do espaço e visualização do planejamento. Não há integração ou cópia do software GARDENA; a planta foi implementada em SVG no projeto.

As referências orientaram o fluxo de levantamento e planejamento; recomendações de cultivo e execução precisam considerar o local real do cliente.
