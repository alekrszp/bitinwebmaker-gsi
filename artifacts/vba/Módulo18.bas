Attribute VB_Name = "Módulo18"
Sub Lib_Manual()
'
' Liberação manual
'
LINHA = ActiveCell.Row
'
Plan4.Cells(LINHA, 2) = "INSERIR CÓDIGO"
Plan4.Cells(LINHA, 3) = "INSERIR DESCRIÇÃO"

Plan4.Cells(LINHA + 1, 3) = "Alteração de Dados Básicos"
Plan4.Cells(LINHA + 2, 3) = "Campo Alterado"
Plan4.Cells(LINHA + 2, 4) = "De:"
Plan4.Cells(LINHA + 2, 5) = "Para:"

Plan4.Range("A" & LINHA).EntireRow.Font.Bold = True
Plan4.Range("A" & LINHA + 1).EntireRow.Font.Bold = True
Plan4.Range("A" & LINHA + 2).EntireRow.Font.Bold = True


'PINTA CELULAS DA LINHA DO CODIGO ALTERADO
Plan4.Range("B" & LINHA).Interior.Color = vbYellow
Plan4.Range("C" & LINHA).Interior.Color = vbYellow
Plan4.Range("D" & LINHA).Interior.Color = vbYellow
Plan4.Range("E" & LINHA).Interior.Color = vbYellow
Plan4.Range("F" & LINHA).Interior.Color = vbYellow
Plan4.Range("G" & LINHA).Interior.Color = vbYellow
Plan4.Range("H" & LINHA).Interior.Color = vbYellow
Plan4.Range("I" & LINHA).Interior.Color = vbYellow
Plan4.Range("J" & LINHA).Interior.Color = vbYellow
Plan4.Range("K" & LINHA).Interior.Color = vbYellow
Plan4.Range("L" & LINHA).Interior.Color = vbYellow

End Sub

