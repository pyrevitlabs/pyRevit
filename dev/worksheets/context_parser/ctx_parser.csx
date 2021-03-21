public class Condition {
}

public class StrCondition : Condition {
    public string Token { get; set; }
    public override string ToString() => Token;
}

public abstract class CombinedCondition : Condition {
    public bool Main { get; set; } = false;
    public bool Not { get; set; } = false;
    public abstract char Separator { get; }
    public HashSet<Condition> Conditions {get; set;}

    public override string ToString(){
        var repr = string.Join(Separator, Conditions);
        if (Main)
            return repr;
        else
            return (Not ? "!" : "") + "(" + repr + ")";
    }
}

public class AllCondition : CombinedCondition {
    public override char Separator => '&';
}

public class AnyCondition : CombinedCondition {
    public override char Separator => '|';
}

public class ExactCondition : CombinedCondition {
   public override char Separator => ';';
}

public static class Conditions {
    public static Condition FromToken(string token) => new StrCondition { Token = token };
}

public class CtxParser {
    // separators
    const char CONTEXT_CONDITION_ALL_SEP = '&';
    const char CONTEXT_CONDITION_ANY_SEP = '|';
    const char CONTEXT_CONDITION_EXACT_SEP = ';';
    const char CONTEXT_CONDITION_NOT = '!';

    // category name separator for comparisons
    const string SEP = "|";

    public Condition Context = null;

    public override string ToString(){
        return Context?.ToString();
    }

    public CtxParser(string contextString) {
        /*
        * Context string format is a list of tokens joined by either & or | but not both
        * and grouped inside (). Groups can also be joined by either & or | but not both
        * Context strings can not be nested
        * Examples: a,b,c are tokens
        * (a)
        * (a&b&c)
        * (a|b|c)
        * (a|b|c)&(a&b&c)
        * (a|b|c)|(a&b&c)
        */

        // parse context string
        CombinedCondition condition = new AllCondition();
        var collectedConditions = new HashSet<Condition>();

        bool capturingSubCondition = false;
        bool subConditionIsNot = false;
        CombinedCondition subCondition = new AllCondition();
        var  collectedSubConditions = new HashSet<Condition>();

        bool capturingToken = false;
        string currentToken = string.Empty;

        Action captureToken = () => {
            if (capturingToken && currentToken != string.Empty) {
                collectedSubConditions.Add(
                    Conditions.FromToken(currentToken)
                    );
                currentToken = string.Empty;
            }
        };

        Action captureSubConditions = () => {
            if (capturingSubCondition) {
                if (collectedSubConditions.Count > 0) {
                    subCondition.Conditions = collectedSubConditions;
                    subCondition.Not = subConditionIsNot;
                    collectedConditions.Add(subCondition);
                }
                collectedSubConditions = new HashSet<Condition>();
                capturingSubCondition = false;
                subConditionIsNot = false;
            }
        };

        foreach(char c in contextString) {
            switch (c) {
                // sub conditions
                case '(':
                    if (capturingSubCondition)
                        captureToken();
                    else {
                        capturingSubCondition = true;
                        capturingToken = true;
                    }
                    continue;
                case ')':
                    captureToken();
                    captureSubConditions();
                    continue;

                // (sub)condition types
                case CONTEXT_CONDITION_ALL_SEP:
                    captureToken();
                    if (capturingSubCondition) subCondition = new AllCondition();
                    else condition = new AllCondition();
                    continue;
                case CONTEXT_CONDITION_ANY_SEP:
                    captureToken();
                    if (capturingSubCondition) subCondition = new AnyCondition();
                    else condition = new AnyCondition();
                    continue;
                case CONTEXT_CONDITION_EXACT_SEP:
                    captureToken();
                    if (capturingSubCondition) subCondition = new ExactCondition();
                    else condition = new ExactCondition();
                    continue;

                case CONTEXT_CONDITION_NOT:
                    if (!capturingSubCondition) subConditionIsNot = true;
                    continue;

                // tokens
                default:
                    if (capturingToken) currentToken += c; continue;
            }
        }

        condition.Conditions = collectedConditions;
        condition.Main = true;
        Context = condition;
    }
}


var TESTS = @"
(a)
(a&b)
(a|b|c)
(a|b)&(c&d)
|(a|b)&(c&d)
(a|b)|(c&d)&(e|f)
(a|b)|(c&d|g&h)&(e|f)
(a|b)|()
(a|b)|(b&c(d&e(f|g)))
(a|b)&(c;d;e)
!(a|b)&!(c;d;e)
!(a|b)&(c;d;e)|()|!(c&d)
(zero-doc)
";

var EXPECTED = @"
(a)
(a&b)
(a|b|c)
(a|b)&(c&d)
|(a|b)&(c&d)
(a|b)|(c&d)&(e|f)
(a|b)|(c&d|g&h)&(e|f)
(a|b)|()
(a|b)|(b&c(d&e(f|g)))
(a|b)&(c;d;e)
!(a|b)&!(c;d;e)
!(a|b)|(c;d;e)|()|!(c&d)
(zero-doc)
";

var expected = EXPECTED.Split('\n');
int index = 0;
foreach(string test in TESTS.Split('\n')) {
    if (!string.IsNullOrEmpty(test)) {
        var res = new CtxParser(test).ToString();
        if (res == expected[index])
        Console.WriteLine($"🍏 PASS \"{test}\" --> {res}");
    }
    index++;
}
