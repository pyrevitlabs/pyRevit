package persistence

import (
	"fmt"
	"strings"
)

func ToSql(values *[]string, wrap bool) string {
	// wrap values in '' first
	cleanedValues := make([]string, 0)
	valueFormat := "%s"
	if wrap {
		for _, value := range *values {
			if value != "" {
				cleanedValues = append(
					cleanedValues,
					fmt.Sprintf("'%s'", strings.Replace(value, "'", "''", -1)))
			} else {
				cleanedValues = append(cleanedValues, "NULL")
			}
		}
	} else {
		for _, value := range *values {
			cleanedValues = append(
				cleanedValues,
				fmt.Sprintf(valueFormat, value))
		}
	}
	// create the (,,,) sql value list
	return fmt.Sprintf("(%s)", strings.Join(cleanedValues, ", "))
}

func ToMap(fields, values *[]string) map[string]string {
	return make(map[string]string)
}
