Attribute VB_Name = "Módulo15"
Sub dados_lista_técnia()
'
LINHA03 = ActiveCell.Row

' dados_lista_técnia Macro
Plan4.Cells(LINHA03, 2) = "INSERIR CÓDIGO"
Plan4.Cells(LINHA03, 3) = "INSERIR DESCRIÇÃO"
Plan4.Cells(LINHA03 + 1, 3) = "Alteração de Lista Técnica"
Plan4.Cells(LINHA03 + 1, 4) = "Centro"
Plan4.Cells(LINHA03 + 1, 5) = "Utilização de Lista Técnica"
Plan4.Cells(LINHA03 + 3, 4) = "Quantidade - De:"
Plan4.Cells(LINHA03 + 3, 5) = "Quantidade - Para:"
Plan4.Cells(LINHA03 + 3, 2) = "Código filho:"
Plan4.Cells(LINHA03 + 3, 3) = "Descrição filho:"
Plan4.Range("A" & LINHA03).EntireRow.Font.Bold = True
Plan4.Range("A" & LINHA03 + 1).EntireRow.Font.Bold = True
Plan4.Range("A" & LINHA03 + 3).EntireRow.Font.Bold = True
Plan4.Range("D" & LINHA03 + 2).Interior.Color = vbYellow
Plan4.Range("E" & LINHA03 + 2).Interior.Color = vbYellow

Plan4.Range("A" & LINHA03).EntireRow.Font.Bold = True
Plan4.Range("A" & LINHA03 + 1).EntireRow.Font.Bold = True
Plan4.Range("A" & LINHA03 + 2).EntireRow.Font.Bold = True


'PINTA CELULAS DA LINHA DO CODIGO ALTERADO
Plan4.Range("B" & LINHA03).Interior.Color = vbYellow
Plan4.Range("C" & LINHA03).Interior.Color = vbYellow
Plan4.Range("D" & LINHA03).Interior.Color = vbYellow
Plan4.Range("E" & LINHA03).Interior.Color = vbYellow
Plan4.Range("F" & LINHA03).Interior.Color = vbYellow
Plan4.Range("G" & LINHA03).Interior.Color = vbYellow
Plan4.Range("H" & LINHA03).Interior.Color = vbYellow
Plan4.Range("I" & LINHA03).Interior.Color = vbYellow
Plan4.Range("J" & LINHA03).Interior.Color = vbYellow
Plan4.Range("K" & LINHA03).Interior.Color = vbYellow
Plan4.Range("L" & LINHA03).Interior.Color = vbYellow

    
End Sub




