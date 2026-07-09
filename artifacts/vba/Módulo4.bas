Attribute VB_Name = "Módulo4"
'PREENCHIMENTO DO FORMULARIO DE BITIN - APRESENTAÇÃO VISUAL
Public LINHA01 As Integer
Public LINHA02 As Integer
Public Sub Preencher_Bitin()

'Preenchimento campo solicitante

usuario = Planilha1.Cells(2, 30)
Plan4.Cells(3, 8) = Application.WorksheetFunction.VLookup((usuario), Planilha1.Range("ae:af"), 2, 0)
Plan4.Cells(2, 7) = Application.WorksheetFunction.VLookup((usuario), Planilha1.Range("ae:ah"), 4, 0)

LINHA01 = 33  'LINHA DO TEMPLATE DO BITIN
LINHA02 = 5 ' LINHA DA ABA ZBPP009 + ALTERAÇÃO
LINHA_FINAL = LINHA01
Data = Format(DateTime, "dd.mm.yyyy")

'ENCONTRAR LINHA VAZIA
Do While Plan4.Cells(LINHA01, 2).Value <> Empty
LINHA01 = LINHA01 + 1
Loop

Do While Plan2.Cells(LINHA02, 5).Value <> Empty

LINHA01 = LINHA_FINAL

Plan4.Cells(LINHA01, 2) = Plan2.Cells(LINHA02, 5).Value 'Código
Plan4.Cells(LINHA01, 3) = Plan2.Cells(LINHA02, 6).Value 'Descrição

'Preenchimentos dos campos de alteração (ESP, LP, PRE, OC e OF)
Plan4.Range("D" & LINHA01).EntireRow.Font.Bold = True
Plan4.Cells(LINHA01, 7) = Plan2.Cells(LINHA02, 75).Value 'Preenche estoque
Plan4.Cells(LINHA01, 9) = Plan2.Cells(LINHA02, 76).Value 'Preenche Lp
Plan4.Cells(LINHA01, 10) = Plan2.Cells(LINHA02, 77).Value 'Preenche PRE
Plan4.Cells(LINHA01, 11) = Plan2.Cells(LINHA02, 78).Value 'Preenche OC
Plan4.Cells(LINHA01, 12) = Plan2.Cells(LINHA02, 79).Value 'Preenche OF

'PINTA CELULAS DA LINHA DO CODIGO ALTERADO
Plan4.Range("B" & LINHA01).Interior.Color = 16777164
Plan4.Range("C" & LINHA01).Interior.Color = 16777164
Plan4.Range("D" & LINHA01).Interior.Color = 16777164
Plan4.Range("F" & LINHA01).Interior.Color = 16777164
Plan4.Range("G" & LINHA01).Interior.Color = 16777164
Plan4.Range("H" & LINHA01).Interior.Color = 16777164
Plan4.Range("I" & LINHA01).Interior.Color = 16777164
Plan4.Range("J" & LINHA01).Interior.Color = 16777164
Plan4.Range("K" & LINHA01).Interior.Color = 16777164
Plan4.Range("L" & LINHA01).Interior.Color = 16777164
Plan4.Range("E" & LINHA01).Interior.Color = 16777164

'TRECHO DO PREENCHIMENTO DA COLUNA ALTERAÇÃO DO BITIN________________________________________________________________________________________________________________________________

'Fim do trecho TRECHO DO PREENCHIMENTO DA COLUNA ALTERAÇÃO DO BITIN
'REGRA PARA PREENCHIMENTO DA ALTERAÇÃO
If Plan2.Cells(LINHA02, 24) = "SIM" Then 'seção que verifica se tem alteração de desenho
    If Plan2.Cells(LINHA02, 27) <> Empty Then 'Verifica se mudou nivel de revisao
        Call DWG_SAT 'Chama o Modulo 10
            If Left(Plan2.Cells(LINHA02, 9), 2) = "MP" Then
                Plan4.Cells(LINHA01, 6) = "D/F"
            ElseIf Left(Plan2.Cells(LINHA02, 8), 2) = "MP" Then
                Plan4.Cells(LINHA01, 6) = "D/F"
                
                ElseIf Plan2.Cells(LINHA02, 8) = "SA014" Then
                    If Plan2.Cells(LINHA02, 9) = Empty Then
                    Plan4.Cells(LINHA01, 6) = "D/F"
                    Else
                    End If
                
                ElseIf Plan2.Cells(LINHA02, 8) <> "SA014" Then
                    If Plan2.Cells(LINHA02, 9) = "SA014" Then
                        Plan4.Cells(LINHA01, 6) = "D/F"
                Else
                        Plan4.Cells(LINHA01, 6) = "D/P"
                    End If
            End If
    Else
     Call DWG_SAT_N_DESENHO 'Chama o Modulo 13
        If Plan2.Cells(LINHA02, 8) = "SA014" Then
            If Plan2.Cells(LINHA02, 9) = Empty Then
            Plan4.Cells(LINHA01, 6) = "-/F"
            Else
            End If
        ElseIf Plan2.Cells(LINHA02, 8) <> "SA014" Then
            If Plan2.Cells(LINHA02, 9) = "SA014" Then
            Plan4.Cells(LINHA01, 6) = "-/F"
            Else
                Plan4.Cells(LINHA01, 6) = "-"
            End If
        Else
        End If
    End If
'-----------------------------------------------------------------
Else
 
    If Plan2.Cells(LINHA02, 67) <> Empty Then 'seção que verifica se tem alteração no texto pedido compras
        If Left(Plan2.Cells(LINHA02, 8), 2) = "MP" Then 'verifica se o item é comprado
        Plan4.Cells(LINHA01, 6) = "-/F"
        Else
            If Left(Plan2.Cells(LINHA02, 9), 2) = "MP" Then
            Plan4.Cells(LINHA01, 6) = "-/F"
            ElseIf Plan2.Cells(LINHA02, 8) = "SA014" Then 'verifica se o item é subcontratado
                If Plan2.Cells(LINHA02, 9) = Empty Then
                Plan4.Cells(LINHA01, 6) = "-/F"
                Else
                End If
                ElseIf Plan2.Cells(LINHA02, 8) <> "SA014" Then 'verifica se o item é subcontratado
                    If Plan2.Cells(LINHA02, 9) = "SA014" Then
                    Plan4.Cells(LINHA01, 6) = "-/F"
                    Else
                    Plan4.Cells(LINHA01, 6) = "-"
                    End If
            End If
        End If
    End If
'----
End If
'------------------------------------------------------------------------------------------------------------------------------------------------------------
'REGRA PARA PREENCHIMENTO DA ESPECIFICAÇÃO TÉCNICA
If Plan2.Cells(LINHA02, 67) <> Empty Then
If Plan2.Cells(LINHA02, 67) <> "N/A" Then
    If Left(Plan2.Cells(LINHA02, 8), 2) = "MP" Then
        Plan4.Cells(LINHA01, 8) = "X"
        ElseIf Left(Plan2.Cells(LINHA02, 9), 2) = "MP" Then
        Plan4.Cells(LINHA01, 8) = "X"
            ElseIf Plan2.Cells(LINHA02, 8) <> "SA014" Then
            If Plan2.Cells(LINHA02, 9) = "SA014" Then
            Plan4.Cells(LINHA01, 8) = "X"
            End If
                ElseIf Plan2.Cells(LINHA02, 8) = "SA014" Then
                If Plan2.Cells(LINHA02, 67) <> Empty Then
                Plan4.Cells(LINHA01, 8) = "X"
                End If
    End If
End If
End If
If Plan4.Cells(LINHA01, 8) <> "X" Then
Plan4.Cells(LINHA01, 8) = "-"
End If

'------------------------------------------------------------------------------------------------------------------------------------------------------------
'PREENCHER CHECK LIST

'DESENHO, PROCESSO E FORNECEDOR
If Plan4.Cells(LINHA01, 6) = "D/P" Then
Plan4.Cells(9, 3) = "SIM"
ElseIf Plan4.Cells(LINHA01, 6) = "D/-" Then
Plan4.Cells(8, 3) = "SIM"
ElseIf Plan4.Cells(LINHA01, 6) = "-/P" Then
Plan4.Cells(11, 3) = "SIM"
ElseIf Plan4.Cells(LINHA01, 6) = "D/F" Then
Plan4.Cells(10, 3) = "SIM"
ElseIf Plan4.Cells(LINHA01, 6) = "-/F" Then
Plan4.Cells(12, 3) = "SIM"
End If

'Atualizar DWG / SAT
If Plan4.Cells(LINHA01, 4) <> Empty Then
    If Plan4.Cells(LINHA01, 4) = "SALVAR DWG" Then
    Plan4.Cells(22, 3) = "SIM"
    ElseIf Plan4.Cells(LINHA01, 4) = "SALVAR SAT" Then
    Plan4.Cells(22, 3) = "SIM"
    End If
End If

'ESTOQUE
If Plan4.Cells(LINHA01, 7) <> Empty Then
If Plan4.Cells(LINHA01, 7) <> "-" Then
Plan4.Cells(15, 3) = "SIM"
End If
End If

If Plan4.Cells(LINHA01, 7) = "S" Then
Plan4.Cells(26, 3) = "SIM"
End If

'LISTA DE PREÇO
If Plan4.Cells(LINHA01, 9) <> Empty Then
If Plan4.Cells(LINHA01, 9) <> "-" Then
Plan4.Cells(23, 3) = "SIM"
End If
End If

'PRECIFICAÇÃO
If Plan4.Cells(LINHA01, 10) <> Empty Then
If Plan4.Cells(LINHA01, 10) <> "-" Then
Plan4.Cells(24, 3) = "SIM"
End If
End If

'ORDEM DE CLIENTE
If Plan4.Cells(LINHA01, 11) <> Empty Then
If Plan4.Cells(LINHA01, 11) <> "-" Then
Plan4.Cells(17, 3) = "SIM"
End If
End If

'ORDEM DE FABRICAÇÃO
If Plan4.Cells(LINHA01, 12) <> Empty Then
If Plan4.Cells(LINHA01, 12) <> "-" Then
Plan4.Cells(21, 3) = "SIM"
End If
End If

'INSERIR DADO PARA REVISAR ROTEIRO
If Plan4.Cells(LINHA01, 6) = "D/P" Then
Plan4.Cells(LINHA01, 5) = "REVISAR ROTEIRO"
ElseIf Plan4.Cells(LINHA01, 6) = "-/P" Then
Plan4.Cells(LINHA01, 5) = "REVISAR ROTEIRO"
End If

'------------------------------------------------------------------------------------------------------------------------------------------------------------
Plan4.Cells(LINHA01 + 1, 3) = "Alteração de Dados Básicos no Centro:"
Plan4.Cells(LINHA01 + 1, 4) = Plan2.Cells(LINHA02, 4)
Plan4.Cells(LINHA01 + 2, 3) = "Campo alterado"
Plan4.Cells(LINHA01 + 2, 4) = "De:"
Plan4.Cells(LINHA01 + 2, 5) = "Para:"
Plan4.Range("D" & LINHA01 + 1).EntireRow.Font.Bold = True
Plan4.Range("D" & LINHA01 + 2).EntireRow.Font.Bold = True


coluna = 7
Do While coluna < 75

'Regra N/A -
If coluna = 31 Then
GoTo RegraNA

ElseIf coluna = 33 Then
GoTo RegraNA

ElseIf coluna = 35 Then
GoTo RegraNA

ElseIf coluna = 43 Then
GoTo RegraNA

ElseIf coluna = 49 Then
GoTo RegraNA

ElseIf coluna = 51 Then
GoTo RegraNA

ElseIf coluna = 53 Then
GoTo RegraNA

ElseIf coluna = 55 Then
GoTo RegraNA

ElseIf coluna = 57 Then
GoTo RegraNA

ElseIf coluna = 59 Then
GoTo RegraNA

ElseIf coluna = 65 Then
GoTo RegraNA

ElseIf coluna = 67 Then
GoTo RegraNA

Else
GoTo RegraGeral

RegraNA:
If Plan2.Cells(LINHA02, coluna).Value <> "N/A" Then
GoTo Preenchimento_Bitin
Else
GoTo Next_Coluna
End If

RegraGeral:
If Plan2.Cells(LINHA02, coluna).Value <> Empty Then
GoTo Preenchimento_Bitin
Else
GoTo Next_Coluna
End If

End If

Preenchimento_Bitin: '___________________________________________________________________________________________________________________________________________________________________

Plan4.Cells(2, 10) = Plan2.Cells(1, 2).Value 'Numero BITIN
Plan4.Cells(3, 4) = Plan2.Cells(2, 2).Value 'PRODUTO
Plan4.Cells(4, 4) = Plan2.Cells(3, 2).Value 'Motivo
Plan4.Cells(4, 8) = Data
Plan4.Cells(LINHA01 + 3, 3) = Plan2.Cells(4, coluna - 1).Value 'Descrição
Plan4.Cells(LINHA01 + 3, 4) = Plan2.Cells(LINHA02, coluna - 1).Value 'Descrição Antiga
Plan4.Cells(LINHA01 + 3, 5) = Plan2.Cells(LINHA02, coluna).Value 'Descrição Nova
'_________________________________________________________________________________________________________________________________________________________________________________________
LINHA_FINAL = LINHA01 + 6
LINHA01 = LINHA01 + 1
Next_Coluna:
coluna = coluna + 2 '(vai pulandoa coluna de 2 em 2)

Loop 'final do loop da coluna
LINHA_FINAL = LINHA01 + 6
'Adicionar linha divisória no template de apresentação__________________________________________________________________________________________________________________________________

'----------------------------------------------------------------------------------------------------------
'If Plan2.Cells(LINHA02, 76).Value = "-" Or Plan2.Cells(LINHA02, 77).Value = Empty Then  'Preencher linha solicitando precificar
'Plan4.Cells(LINHA01, 5) = "Precificar"
'End If
'----------------------------------------------------------------------------------------------------------
'Vai preencher se o campo marcação de eliminação for = sim, então preenche o terxo de não calcular custo (execução manual)
'If Plan2.Cells(LINHA02, 69) = "SIM" Then
'Rows(LINHA01).Select
   ' Selection.Insert Shift:=xlDown, CopyOrigin:=xlFormatFromLeftOrAbove
'Plan4.Cells(LINHA01, 3) = "Bloqueio cálculo de custos"
'Plan4.Cells(LINHA01, 5) = "X"
'End If

Plan4.Rows(LINHA01 + 4).Interior.Color = vbBlack

Plan4.Rows(LINHA01 + 4).RowHeight = 6.75

'LINHA_FINAL = LINHA01 + 6
'LINHA01 = LINHA01 + 1

'Alterar linha na aba zbpp009
LINHA02 = LINHA02 + 1

Loop 'final do loop da linha

 MsgBox "BITin criado com sucesso!"

End Sub






