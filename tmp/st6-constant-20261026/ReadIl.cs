// メーカー同梱の変数読込みメソッドを、実行せずIL命令として調査する。
using System;
using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
using System.Text;
public static class ReadIl {
 public static string Dump(MethodBase method) {
  var codes=new Dictionary<short,OpCode>();
  foreach(var f in typeof(OpCodes).GetFields(BindingFlags.Public|BindingFlags.Static)) {
   if(f.FieldType==typeof(OpCode)){var op=(OpCode)f.GetValue(null);codes[op.Value]=op;}
  }
  var bytes=method.GetMethodBody().GetILAsByteArray();var output=new StringBuilder();int i=0;
  while(i<bytes.Length) {
   int offset=i;short key=bytes[i++];if(key==0xfe)key=(short)(0xfe00|bytes[i++]);var op=codes[key];
   int count=0;object arg="";
   switch(op.OperandType) {
    case OperandType.InlineNone:break;
    case OperandType.ShortInlineBrTarget:case OperandType.ShortInlineI:case OperandType.ShortInlineVar: count=1;arg=bytes[i];break;
    case OperandType.InlineVar:count=2;arg=BitConverter.ToUInt16(bytes,i);break;
    case OperandType.InlineI8:case OperandType.InlineR:count=8;arg=BitConverter.ToInt64(bytes,i);break;
    case OperandType.InlineSwitch:count=4+4*BitConverter.ToInt32(bytes,i);arg="switch";break;
    default:
     count=4;int token=BitConverter.ToInt32(bytes,i);arg=token;
     try {
      if(op.OperandType==OperandType.InlineString)arg="\""+method.Module.ResolveString(token)+"\"";
      else if(op.OperandType==OperandType.InlineMethod||op.OperandType==OperandType.InlineField||op.OperandType==OperandType.InlineType||op.OperandType==OperandType.InlineTok)arg=method.Module.ResolveMember(token);
     } catch {}
     break;
   }
   output.AppendFormat("{0:x4} {1} {2}\n",offset,op.Name,arg);i+=count;
  }
  return output.ToString();
 }
}
