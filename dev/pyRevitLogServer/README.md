Legacy schema

```sql
CREATE TABLE public.pyrevitusage (
	"date" date NULL,
	"time" time NULL,
	username varchar(255) NULL,
	revit varchar(255) NULL,
	revitbuild varchar(255) NULL,
	sessionid varchar(255) NULL,
	pyrevit varchar(255) NULL,
	debug bool NULL,
	alternate bool NULL,
	commandname varchar(255) NULL,
	commandbundle varchar(255) NULL,
	commandextension varchar(255) NULL,
	commanduniquename text NULL,
	resultcode int4 NULL,
	commandresults json NULL,
	scriptpath text NULL,
	traceenginever varchar(255) NULL,
	traceipy text NULL,
	traceclr text NULL
);
```


Schema 2.0

```sql
CREATE TABLE public.pyrevitusage (
	recordid uuid NOT NULL,
	"timestamp" timestamp NULL,
	username varchar(255) NULL,
	revit varchar(255) NULL,
	revitbuild varchar(255) NULL,
	sessionid varchar(255) NULL,
	pyrevit varchar(255) NULL,
	debug bool NULL,
	alternate bool NULL,
	commandname varchar(255) NULL,
	commandbundle varchar(255) NULL,
	commandextension varchar(255) NULL,
	commanduniquename text NULL,
	resultcode int4 NULL,
	commandresults json NULL,
	scriptpath text NULL,
	traceenginetype varchar(255) NULL,
	traceenginever varchar(255) NULL,
	tracemsg text NULL,
	CONSTRAINT pyrevitusage2_pk PRIMARY KEY (recordid)
);
```