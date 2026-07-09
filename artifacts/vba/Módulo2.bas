Attribute VB_Name = "Módulo2"
Function DateTime()
DateTime = Now
End Function
Public Sub Winshuttle()

'https://www.youtube.com/watch?v=yw8tfKbNezs
Dim Linha2, Linha3 As Integer

Data = Format(DateTime, "dd.mm.yyyy")

BITIN = Plan2.Cells(1, 2).Value
Produto = Plan2.Cells(2, 2).Value
Motivo = Plan2.Cells(3, 2).Value

Linha2 = 5
Linha3 = 3

Do Until Plan2.Cells(Linha2, 3).Value = Empty

'Envia dados entre as abas abaixo:
'FORMULÁRIO WINSHUTTE_____ZBPP009 + ALTERAÇÃO

'Cadastro do BITin
Plan3.Cells(Linha3, 1) = BITIN 'NUMERO BITIN
Plan3.Cells(Linha3, 2) = Produto 'PRODUTO
Plan3.Cells(Linha3, 3) = Motivo 'MOTIVO
Plan3.Cells(Linha3, 4) = Data
Plan3.Cells(Linha3, 6) = "SIM"
Plan3.Cells(Linha3, 106) = Plan2.Cells(Linha2, 3).Value 'TIPO MATERIAL
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 10) = Plan2.Cells(Linha2, 4).Value 'CENTRO
Plan3.Cells(Linha3, 9) = Plan2.Cells(Linha2, 5).Value 'CÓDIGO
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 12) = Plan2.Cells(Linha2, 7).Value 'DESCRIÇÃO
If Plan3.Cells(Linha3, 12) = Empty Then
Plan3.Cells(Linha3, 11) = ""
Else
Plan3.Cells(Linha3, 11) = "SIM"
End If
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 14) = Plan2.Cells(Linha2, 9).Value 'GRUPO DE MERCADORIAS
If Plan3.Cells(Linha3, 14) = Empty Then
Plan3.Cells(Linha3, 13) = ""
Else
Plan3.Cells(Linha3, 13) = "SIM"
End If
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 16) = Plan2.Cells(Linha2, 11).Value 'STATUS
If Plan3.Cells(Linha3, 16) = Empty Then
Plan3.Cells(Linha3, 15) = ""
Else
Plan3.Cells(Linha3, 15) = "SIM"
End If
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 18) = Plan2.Cells(Linha2, 13).Value 'HIERARQUIA
If Plan3.Cells(Linha3, 18) = Empty Then
Plan3.Cells(Linha3, 17) = ""
Else
Plan3.Cells(Linha3, 17) = "SIM"
End If
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 20) = Plan2.Cells(Linha2, 15).Value 'PESO BRUTO
If Plan3.Cells(Linha3, 20) = Empty Then
Plan3.Cells(Linha3, 19) = ""
Else
Plan3.Cells(Linha3, 19) = "SIM"
End If
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 22) = Plan2.Cells(Linha2, 17).Value 'PESO LIQUIDO
If Plan3.Cells(Linha3, 22) = Empty Then
Plan3.Cells(Linha3, 21) = ""
Else
Plan3.Cells(Linha3, 21) = "SIM"
End If
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 24) = Plan2.Cells(Linha2, 19).Value 'UNIDADE PESO
If Plan3.Cells(Linha3, 24) = Empty Then
Plan3.Cells(Linha3, 23) = ""
Else
Plan3.Cells(Linha3, 23) = "SIM"
End If
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 26) = Plan2.Cells(Linha2, 21).Value 'VOLUME
If Plan3.Cells(Linha3, 26) = Empty Then
Plan3.Cells(Linha3, 25) = ""
Else
Plan3.Cells(Linha3, 25) = "SIM"
End If
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 28) = Plan2.Cells(Linha2, 23).Value 'UNIDADE VOLUME
If Plan3.Cells(Linha3, 28) = Empty Then
Plan3.Cells(Linha3, 27) = ""
Else
Plan3.Cells(Linha3, 27) = "SIM"
End If
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 30) = Plan2.Cells(Linha2, 25).Value 'DESENHO
If Plan3.Cells(Linha3, 30) = Empty Then
Plan3.Cells(Linha3, 29) = ""
Else
Plan3.Cells(Linha3, 29) = "SIM"
End If
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 32) = Plan2.Cells(Linha2, 27).Value 'NIVEL REVISAO
If Plan3.Cells(Linha3, 32) = Empty Then
Plan3.Cells(Linha3, 31) = ""
Else
Plan3.Cells(Linha3, 31) = "SIM"
End If
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 38) = Plan2.Cells(Linha2, 29).Value 'DOCUMENTO
If Plan3.Cells(Linha3, 38) = Empty Then
Plan3.Cells(Linha3, 37) = ""
Else
Plan3.Cells(Linha3, 37) = "SIM"
End If
'----------------------------------------------------------------------------
If Plan2.Cells(Linha2, 31) <> "N/A" Then    'MATERIAL SUBSTITUTO
Plan3.Cells(Linha3, 39) = "SIM"
Plan3.Cells(Linha3, 40) = Plan2.Cells(Linha2, 31)
Else
End If
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 42) = Plan2.Cells(Linha2, 33).Value 'STATUS BLOQUEIO DE VENDAS
If Plan2.Cells(Linha2, 33) = "N/A" Then
Plan3.Cells(Linha3, 41) = ""
Else
Plan3.Cells(Linha3, 41) = "SIM"
End If
Plan3.Cells(Linha3, 43) = Plan2.Cells(Linha2, 35).Value 'DATA BLOQUEIO DE VENDAS
'----------------------------------------------------------------------------
'Plan3.Cells(Linha3, 45) = Plan2.Cells(Linha2, 37).Value 'GRUPO ESTAT. MATERIAL
'If Plan3.Cells(Linha3, 45) = Empty Then
'Plan3.Cells(Linha3, 44) = ""
'Else
'Plan3.Cells(Linha3, 44) = "SIM"
'End If
'Plan3.Cells(Linha3, 46) = Plan2.Cells(Linha2, 39).Value 'GRUPO ESTAT. MATERIAL
'If Plan3.Cells(Linha3, 46) = Empty Then
'Plan3.Cells(Linha3, 44) = ""
'Else
'Plan3.Cells(Linha3, 44) = "SIM"
'End If
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 48) = Plan2.Cells(Linha2, 41).Value 'NCM
If Plan3.Cells(Linha3, 48) = Empty Then
Plan3.Cells(Linha3, 47) = ""
Else
Plan3.Cells(Linha3, 47) = "SIM"
End If
'----------------------------------------------------------------------------
If Plan2.Cells(Linha2, 43) <> "N/A" Then    'GRUPO DE COMPRADORES
Plan3.Cells(Linha3, 51) = "SIM"
Plan3.Cells(Linha3, 52) = Plan2.Cells(Linha2, 43)
Else
End If
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 54) = Plan2.Cells(Linha2, 45).Value 'PLANEJADOR
If Plan3.Cells(Linha3, 54) = Empty Then
Plan3.Cells(Linha3, 53) = ""
Else
Plan3.Cells(Linha3, 53) = "SIM"
End If
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 56) = Plan2.Cells(Linha2, 47).Value 'TIPO DE SUPRIMENTO
If Plan3.Cells(Linha3, 56) = Empty Then
Plan3.Cells(Linha3, 55) = ""
Else
Plan3.Cells(Linha3, 55) = "SIM"
End If
'----------------------------------------------------------------------------

If Plan2.Cells(Linha2, 49) <> "N/A" Then    'TIPO DE SUPRIMENTO eSPECIAL
Plan3.Cells(Linha3, 57) = "SIM"
Plan3.Cells(Linha3, 58) = Plan2.Cells(Linha2, 49)
Else
End If
'---------------------------------------------------------------------------
If Plan2.Cells(Linha2, 51) <> "N/A" Then    'DEPOSITO PRODUÇÃO
Plan3.Cells(Linha3, 59) = "SIM"
Plan3.Cells(Linha3, 60) = Plan2.Cells(Linha2, 51)
Else
End If
'----------------------------------------------------------------------------
If Plan2.Cells(Linha2, 53) <> "N/A" Then    'DEPOSITO SUPRIMENTO EXTERNO
Plan3.Cells(Linha3, 61) = "SIM"
Plan3.Cells(Linha3, 62) = Plan2.Cells(Linha2, 53)
Else
End If
'----------------------------------------------------------------------------
If Plan2.Cells(Linha2, 55) <> "N/A" Then    'PRAZO DE ENTREGA
Plan3.Cells(Linha3, 63) = "SIM"
Plan3.Cells(Linha3, 64) = Plan2.Cells(Linha2, 55)
Else
End If
'----------------------------------------------------------------------------
If Plan2.Cells(Linha2, 57) <> "N/A" Then    'RESP. CRTL.PRODUCAO
Plan3.Cells(Linha3, 65) = "SIM"
Plan3.Cells(Linha3, 66) = Plan2.Cells(Linha2, 57)
Else
End If
'----------------------------------------------------------------------------
If Plan2.Cells(Linha2, 59) <> "N/A" Then    'PERFIL DE PRODUCAO
Plan3.Cells(Linha3, 65) = "SIM"
Plan3.Cells(Linha3, 67) = Plan2.Cells(Linha2, 59)
Else
End If
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 69) = Plan2.Cells(Linha2, 61).Value 'UTILIZAÇÃO MATERIAL
If Plan3.Cells(Linha3, 69) = Empty Then
Plan3.Cells(Linha3, 68) = ""
Else
Plan3.Cells(Linha3, 68) = "SIM"
End If
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 71) = Plan2.Cells(Linha2, 63).Value 'ORIGEM MATERIAL
If Plan3.Cells(Linha3, 71) = Empty Then
Plan3.Cells(Linha3, 70) = ""
Else
Plan3.Cells(Linha3, 70) = "SIM"
End If
'----------------------------------------------------------------------------
If Plan2.Cells(Linha2, 65) <> "N/A" Then    'PRODUÇÃO INTERNA
Plan3.Cells(Linha3, 72) = "SIM"
Plan3.Cells(Linha3, 73) = Plan2.Cells(Linha2, 65)
Else
End If
'----------------------------------------------------------------------------
If Plan2.Cells(Linha2, 67) <> "N/A" Then    'TEXTO PEDIDO DE COMPRAS
Plan3.Cells(Linha3, 74) = "SIM"
Plan3.Cells(Linha3, 75) = Plan2.Cells(Linha2, 67)
Else
End If
'----------------------------------------------------------------------------
Plan3.Cells(Linha3, 82) = Plan2.Cells(Linha2, 69).Value 'MARCAÇÃO PARA ELIMINAR NIVEL MANDANTE
'If Plan3.Cells(Linha2, 82) = "X" Then
'Plan2.Cells(Linha2, 69) = "SIM"
'End If
If Plan2.Cells(Linha2, 71) = "SIM" Then
Plan3.Cells(Linha3, 82) = "SIM"
End If
'----------------------------------------------------------------------------
    Linha2 = Linha2 + 1
    Linha3 = Linha3 + 1

Loop

 MsgBox "Dados enviados com sucesso!"

Plan4.Cells(4, 8) = Data
 
End Sub
 












