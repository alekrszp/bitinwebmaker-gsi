Attribute VB_Name = "Módulo13"
'ROTINA DWG/SAT
Sub DWG_SAT_N_DESENHO()
If Plan2.Cells(LINHA02, 9) <> Empty Then
    If Plan2.Cells(LINHA02, 9) = "SA003" Then
    Plan4.Cells(LINHA01, 4) = "SALVAR DWG"
    ElseIf Plan2.Cells(LINHA02, 9) = "SA016" Then
    Plan4.Cells(LINHA01, 4) = "SALVAR DWG"
    ElseIf Plan2.Cells(LINHA02, 9) = "SA017" Then
    Plan4.Cells(LINHA01, 4) = "SALVAR DWG"
    ElseIf Plan2.Cells(LINHA02, 9) = "SA013" Then
    Plan4.Cells(LINHA01, 4) = "SALVAR SAT"

    Else
    End If
Else
End If

End Sub

