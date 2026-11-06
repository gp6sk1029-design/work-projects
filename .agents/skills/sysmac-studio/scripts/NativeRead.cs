// メーカー同梱の読込み・モデル化・コイル接続を検査する。コンパイラ/実機検査ではない。
using System;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Collections;
using System.Collections.Generic;
using System.Text;
public static class SysmacSkillNativeCheck {
 static object Get(object obj,string name) {return obj.GetType().GetProperty(name).GetValue(obj,null);}
 public static Dictionary<string,object> Check(string source,string installRoot) {
  var assembly=Assembly.LoadFrom(Path.Combine(installRoot,"Modules","Nex","NexProgramming.dll"));
  var parserType=assembly.GetType("NexProgramming.LadderDiagram.Implementation.CompactLadderConverter.CompactRungToStringConverter",true);
  var converterType=assembly.GetType("NexProgramming.LadderDiagram.Implementation.CompactLadderConverter.CompactRungToNormalRungConverter",true);
  var parser=Activator.CreateInstance(parserType);
  int rows=0,parseFail=0,modelFail=0,coils=0,missing=0;
  var parts=new List<Dictionary<string,object>>();var errors=new List<string>();
  using(var zip=ZipFile.OpenRead(source)) foreach(var entry in zip.Entries) {
   if(!entry.FullName.EndsWith(".xml",StringComparison.OrdinalIgnoreCase))continue;
   using(var reader=new StreamReader(entry.Open(),Encoding.UTF8,true)) {
    string line;int count=0;
    while((line=reader.ReadLine())!=null) {
     if(String.IsNullOrWhiteSpace(line))continue;
     if(!line.TrimStart().StartsWith("{")||!line.Contains("\"CLs\""))break;
     int index=count++;rows++;
     try {
      var args=new object[]{line,null};
      if(!(bool)parserType.GetMethod("TryConvertBack").Invoke(parser,args)) {parseFail++;errors.Add(entry.FullName+":"+index+":parse");continue;}
      var converter=Activator.CreateInstance(converterType,new object[]{args[1]});var output=new object[]{null};
      if(!(bool)converterType.GetMethod("TryConvert").Invoke(converter,output)) {modelFail++;errors.Add(entry.FullName+":"+index+":model");continue;}
      foreach(var node in (IEnumerable)Get(output[0],"DiagramNodes")) {
       if(node.GetType().Name!="Coil")continue;
       coils++;int input=0,other=0;
       foreach(var cp in (IEnumerable)Get(node,"ConnectionPoints")) {
        int countEdges=0;foreach(var edge in (IEnumerable)Get(cp,"Edges"))countEdges++;
        if((bool)Get(cp,"IsInputConnection"))input+=countEdges;else other+=countEdges;
       }
       if(input==0||other==0) {missing++;errors.Add(entry.FullName+":"+index+":coil:"+Get(node,"Variable"));}
      }
     }catch(Exception exc) {modelFail++;errors.Add(entry.FullName+":"+index+":"+exc.GetBaseException().Message);}
    }
    if(count>0)parts.Add(new Dictionary<string,object>{{"part",entry.FullName},{"rows",count}});
   }
  }
  return new Dictionary<string,object>{{"rows",rows},{"coils",coils},{"parse_fail",parseFail},{"model_fail",modelFail},{"missing_connections",missing},{"parts",parts},{"errors",errors},{"verified",rows>0&&parseFail==0&&modelFail==0&&missing==0}};
 }
}
