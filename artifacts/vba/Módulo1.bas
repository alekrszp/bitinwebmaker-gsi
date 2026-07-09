Attribute VB_Name = "Módulo1"
Public Sub PREENCHER()
'https://www.youtube.com/watch?v=yw8tfKbNezs

Dim Linha1, Linha2 As Integer

Linha1 = 2
Linha2 = 5

Do Until Plan1.Cells(Linha1, 1).Value = Empty

'ZBPP009 + ALTERACAO_____ZBPP009
Plan2.Cells(Linha2, 3) = Plan1.Cells(Linha1, 1).Value 'TIPO DO MATERIAL
Plan2.Cells(Linha2, 4) = Plan1.Cells(Linha1, 4).Value 'CENTRO
Plan2.Cells(Linha2, 5) = Plan1.Cells(Linha1, 2).Value 'CÓDIGO
Plan2.Cells(Linha2, 6) = Plan1.Cells(Linha1, 5).Value 'DESCRIÇÃO
Plan2.Cells(Linha2, 8) = Plan1.Cells(Linha1, 6).Value 'GRUPO DE MERCADORIAS
Plan2.Cells(Linha2, 10) = Plan1.Cells(Linha1, 7).Value 'STATUS
Plan2.Cells(Linha2, 12) = Plan1.Cells(Linha1, 8).Value 'HIERARQUIA
Plan2.Cells(Linha2, 14) = Plan1.Cells(Linha1, 9).Value 'PESO BRUTO
Plan2.Cells(Linha2, 16) = Plan1.Cells(Linha1, 10).Value 'PESO LIQUIDO
Plan2.Cells(Linha2, 18) = Plan1.Cells(Linha1, 11).Value 'UNIDADE PESO
Plan2.Cells(Linha2, 20) = Plan1.Cells(Linha1, 12).Value 'VOLUME
Plan2.Cells(Linha2, 22) = Plan1.Cells(Linha1, 13).Value 'UNIDADE VOLUME
Plan2.Cells(Linha2, 24) = Plan1.Cells(Linha1, 14).Value 'DESENHO
Plan2.Cells(Linha2, 26) = Plan1.Cells(Linha1, 15).Value 'NIVEL REVISAO
Plan2.Cells(Linha2, 28) = Plan1.Cells(Linha1, 16).Value 'DOCUMENTO

Plan2.Cells(Linha2, 30) = Plan1.Cells(Linha1, 17).Value 'MATERIAL SUBSTITUTO
Plan2.Cells(Linha2, 31) = "N/A" 'MATERIAL SUBSTITUTO NOVO

Plan2.Cells(Linha2, 32) = Plan1.Cells(Linha1, 18).Value 'STATUS BLOQUEIO DE VENDAS
Plan2.Cells(Linha2, 33) = "N/A"

Plan2.Cells(Linha2, 34) = Plan1.Cells(Linha1, 19).Value 'DATA BLOQUEIO DE VENDAS
Plan2.Cells(Linha2, 35) = "N/A"

Plan2.Cells(Linha2, 36) = Plan1.Cells(Linha1, 20).Value 'GRUPO ESTAT. MATERIAL

Plan2.Cells(Linha2, 38) = Plan1.Cells(Linha1, 21).Value 'GRUPO DE MATERIAIS

Plan2.Cells(Linha2, 40) = Plan1.Cells(Linha1, 22).Value 'NCM

Plan2.Cells(Linha2, 42) = Plan1.Cells(Linha1, 23).Value 'GRUPO DE COMPRADORES
Plan2.Cells(Linha2, 43) = "N/A" 'GRUPO DE COMPRADORES NOVO

Plan2.Cells(Linha2, 44) = Plan1.Cells(Linha1, 24).Value 'PLANEJADOR
Plan2.Cells(Linha2, 46) = Plan1.Cells(Linha1, 25).Value 'TIPO DE SUPRIMENTO

Plan2.Cells(Linha2, 48) = Plan1.Cells(Linha1, 26).Value 'TIPO SUPRIMENTO ESPECIAL
Plan2.Cells(Linha2, 49) = "N/A" 'TIPO SUPRIMENTO ESPECIAL NOVO

Plan2.Cells(Linha2, 50) = Plan1.Cells(Linha1, 27).Value 'DEPOSITO PRODUÇAO
Plan2.Cells(Linha2, 51) = "N/A" 'DEPOSITO PRODUÇAO NOVO

Plan2.Cells(Linha2, 52) = Plan1.Cells(Linha1, 28).Value 'DEPOSITO SUPRIMENTO EXTERNO
Plan2.Cells(Linha2, 53) = "N/A" 'DEPOSITO SUPRIMENTO EXTERNO NOVO

Plan2.Cells(Linha2, 54) = Plan1.Cells(Linha1, 29).Value 'PRAZO DE ENTREGA
Plan2.Cells(Linha2, 55) = "N/A" 'PRAZO DE ENTREGA NOVO

Plan2.Cells(Linha2, 56) = Plan1.Cells(Linha1, 30).Value 'RESP. CRTL.PRODUCAO
Plan2.Cells(Linha2, 57) = "N/A" 'RESP. CRTL.PRODUCAO NOVO

Plan2.Cells(Linha2, 58) = Plan1.Cells(Linha1, 31).Value 'PERFIL DE PRODUCAO
Plan2.Cells(Linha2, 59) = "N/A" 'PERFIL DE PRODUCAO NOVO

Plan2.Cells(Linha2, 60) = Plan1.Cells(Linha1, 32).Value 'UTILIZAÇÃO MATERIAL
Plan2.Cells(Linha2, 62) = Plan1.Cells(Linha1, 33).Value 'ORIGEM MATERIAL

Plan2.Cells(Linha2, 64) = Plan1.Cells(Linha1, 34).Value 'PRODUCAO INTERNA
Plan2.Cells(Linha2, 65) = "N/A" 'PRODUCAO INTERNA NOVO

Plan2.Cells(Linha2, 66) = Plan1.Cells(Linha1, 35).Value 'TEXTO PEDIDO DE COMPRAS
Plan2.Cells(Linha2, 67) = "N/A" 'TEXTO PEDIDO DE COMPRAS NOVO

'''''Plan2.Cells(Linha2, 68) = Plan1.Cells(Linha1, 36).Value 'MARCAÇÃO PARA ELIMINAR NIVEL MANDANTE
Plan2.Cells(Linha2, 68) = Plan1.Cells(Linha1, 36).Value 'MARCAÇÃO PARA ELIMINAR NIVEL CENTRO

    Linha1 = Linha1 + 1
    Linha2 = Linha2 + 1

Loop
 MsgBox "Dados enviados com sucesso!"

End Sub

'-------------------------------------------------------------------------------------------------------------
