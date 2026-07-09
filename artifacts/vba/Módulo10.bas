Attribute VB_Name = "Módulo10"
'ROTINA DWG/SAT
Sub DWG_SAT()
'Pinta DWG/SAT EM VERMELHO E COLOCA LINHA CÓDIGO EM NEGRITO
    Plan4.Range("D" & LINHA01).EntireRow.Font.Bold = True
    Plan4.Range("D" & LINHA01).Font.Color = vbRed
    
If Plan2.Cells(LINHA02, 8) = "SA003" Then
Plan4.Cells(LINHA01, 4) = "SALVAR DWG"

ElseIf Plan2.Cells(LINHA02, 8) = "SA016" Then
Plan4.Cells(LINHA01, 4) = "SALVAR DWG"

ElseIf Plan2.Cells(LINHA02, 8) = "SA017" Then
Plan4.Cells(LINHA01, 4) = "SALVAR DWG"

ElseIf Plan2.Cells(LINHA02, 8) = "SA013" Then
Plan4.Cells(LINHA01, 4) = "SALVAR SAT"

Else
End If

If Plan2.Cells(LINHA02, 9) <> Empty Then
    If Plan2.Cells(LINHA02, 9) = "SA003" Then
    Plan4.Cells(LINHA01, 4) = "SALVAR DWG"
  

    ElseIf Plan2.Cells(LINHA02, 9) = "SA016" Then
    Plan4.Cells(LINHA01, 4) = "SALVAR DWG"


    ElseIf Plan2.Cells(LINHA02, 9) = "SA017" Then
    Plan4.Cells(LINHA01, 4) = "SALVAR DWG"


    ElseIf Plan2.Cells(LINHA02, 9) = "SA013" Then
    Plan4.Cells(LINHA01, 4) = "SALVAR SAT"

    End If
Else
End If

End Sub

